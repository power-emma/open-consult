"""Sweep sequencing, persistence and fail-stop verification without hardware."""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import c9_direct_sweep as sweep
import c9_direct_test as trial
from consult.experimental import MutationUnverified


class SweepTests(unittest.TestCase):
    def setUp(self):
        self.memory = {0x0817: 0, 0x0818: 0}
        self.attempts = []
        self.clients = []
        self.fail_value = None
        self.error_value = None
        self.fail_address = None

    def client(self):
        client = Mock()
        client.init.return_value = (1, 0.1, b'', 0xED)
        client.part_number.return_value = (b'', '23710-2L904')
        client.read_memory.side_effect = lambda addrs: bytes(self.memory.get(a, 0) for a in addrs)
        pending = []

        def command(payload, **kwargs):
            pending[:] = [(payload[i + 1] << 8) | payload[i + 2]
                          for i in range(0, len(payload), 3)]

        client.command.side_effect = command
        client.read_frame.side_effect = lambda **kwargs: client.read_memory(pending)
        client.stop.return_value = (0xCF, b'')
        self.clients.append(client)
        return client

    def mutation(self, client, command, **kwargs):
        value = command[-1]
        target = 0x07C3 + 2 * ((command[-4] + 1) & 255)
        self.attempts.append(value)
        if value == self.error_value:
            raise MutationUnverified('missing stop acknowledgment')
        self.memory[target] = value if value != self.fail_value and target != self.fail_address else value ^ 1
        self.memory[target + 1] = 0x0E
        return [bytes(17)]

    def run_values(self, values):
        plans = [trial.plan_test(0x0817, value) for value in values]
        report, outcomes = {}, []
        with patch.object(trial, 'mutation_stream', side_effect=self.mutation), \
                patch.object(sweep, 'mutation_stream', side_effect=self.mutation):
            code = sweep.run_sweep(self.client, plans, report,
                                   lambda t, r: outcomes.append(sweep.csv_row(t)))
        return code, report, outcomes

    def test_all_256_values_written_without_skipping_initial_match(self):
        code, report, rows = self.run_values(range(256))
        self.assertEqual(code, 0)
        self.assertEqual(self.attempts, list(range(1, 256)) + [0])
        self.assertEqual(len(rows), 256)
        self.assertTrue(report['all_256_values_verified'])
        self.assertEqual(report['matched_trials'], 256)
        self.assertEqual(report['status'], 'completed')
        self.assertEqual(len(self.clients), 257)
        self.assertEqual(sum(client.init.call_count for client in self.clients), 1)
        self.assertEqual(sum(client.part_number.call_count for client in self.clients), 1)
        self.assertEqual(sum(client.command.call_count for client in self.clients), 1 + 256 * 3)
        self.assertTrue(all(row[3] == row[1] == row[4] for row in rows))

    def test_custom_transitions_use_previous_written_baseline(self):
        code, report, rows = self.run_values([255, 0, 0x21, 0x67])
        self.assertEqual(code, 0)
        self.assertEqual([row[2] for row in rows], ['00', 'FF', '00', '21'])
        self.assertFalse(report['all_256_values_verified'])

    def test_mismatch_stops_before_next_value(self):
        self.fail_value = 2
        code, report, rows = self.run_values([1, 2, 3])
        self.assertEqual(code, 1)
        self.assertEqual(self.attempts, [1, 2])
        self.assertEqual(report['status'], 'stopped_on_mismatch')
        self.assertEqual(report['verified_values'], [1])
        self.assertEqual(len(rows), 2)

    def test_error_stops_without_retry_or_recovery_mutation(self):
        self.error_value = 2
        code, report, rows = self.run_values([1, 2, 3])
        self.assertEqual(code, 2)
        self.assertEqual(self.attempts, [1, 2])
        self.assertEqual(report['status'], 'stopped_on_error')
        self.assertEqual(rows[-1][7], 'unverified')

    def test_same_only_value_is_not_claimed_as_a_write(self):
        code, report, rows = self.run_values([0])
        self.assertEqual(code, 2)
        self.assertEqual(self.attempts, [])
        self.assertEqual(rows[0][7], 'not_attempted')

    def test_parse_ranges_and_reject_invalid_or_trivial_transitions(self):
        self.assertEqual(sweep.parse_values('00-02,FF-FD'), [0, 1, 2, 255, 254, 253])
        self.assertEqual(sweep.parse_values('FF,00,FF'), [255, 0, 255])
        for text in ('', '100', '-1', '00,00', 'GG', '00-100'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                sweep.parse_values(text)

    def test_full_checks_mode_keeps_original_trial_sequence(self):
        plans = [trial.plan_test(0x0817, 1)]
        with patch.object(trial, 'mutation_stream', side_effect=self.mutation):
            report = {}
            self.assertEqual(sweep.run_sweep(self.client, plans, report, lambda t, r: None, fast=False), 0)
        self.assertEqual(report['mode'], 'full_checks')
        self.assertEqual(sum(client.init.call_count for client in self.clients), 3)

    def test_baseline_read_without_stop_ack_cannot_mutate(self):
        client = self.client()
        client.stop.return_value = (None, b'')
        with patch.object(sweep, 'mutation_stream') as mutation:
            with self.assertRaises(sweep.ConsultError):
                sweep.run_fast_trial(client, trial.plan_test(0x0817, 1), {})
            mutation.assert_not_called()

    def test_readback_stop_failure_prevents_followup_read(self):
        client = self.client()
        # Baseline read succeeds; first post-write read has no stop ack.
        client.stop.side_effect = [(0xCF, b''), (None, b'')]
        with patch.object(sweep, 'mutation_stream', side_effect=self.mutation):
            report = {}
            with self.assertRaises(sweep.ConsultError):
                sweep.run_fast_trial(client, trial.plan_test(0x0817, 1), report)
        self.assertTrue(report['mutation_attempted'])
        self.assertNotIn('verification', report)
        self.assertEqual(client.read_frame.call_count, 2)

    def test_fast_engine_running_check_prevents_mutation(self):
        self.memory[0x0994] = 80
        with patch.object(sweep, 'mutation_stream') as mutation:
            with self.assertRaises(sweep.ConsultError):
                sweep.run_fast_trial(self.client(), trial.plan_test(0x0817, 1), {})
            mutation.assert_not_called()

    def run_addresses(self, addresses, **kwargs):
        plans, unsupported = sweep.address_plans(addresses, 0x67)
        report, rows = {}, []
        with patch.object(sweep, 'mutation_stream', side_effect=self.mutation):
            code = sweep.run_sweep(self.client, plans, report,
                                   lambda t, r: rows.append(sweep.csv_row(t)),
                                   address_mode=True, **kwargs)
        return code, report, rows

    def test_fixed_value_at_distinct_addresses(self):
        code, report, rows = self.run_addresses([0x0811, 0x0813, 0x0817])
        self.assertEqual(code, 0)
        self.assertEqual(report['verified_addresses'], [0x0811, 0x0813, 0x0817])
        self.assertTrue(report['all_planned_addresses_verified'])
        self.assertFalse(report['all_256_values_verified'])
        self.assertEqual(self.attempts, [0x67] * 3)
        self.assertEqual([row[-1] for row in rows], ['0811', '0813', '0817'])

    def test_already_matching_address_is_not_counted_as_written(self):
        self.memory[0x0811] = 0x67
        code, report, rows = self.run_addresses([0x0811, 0x0813])
        self.assertEqual(code, 0)
        self.assertEqual(report['verified_addresses'], [0x0813])
        self.assertEqual(report['already_matching_trials'], 1)
        self.assertEqual(self.attempts, [0x67])
        self.assertFalse(report['all_planned_addresses_verified'])
        self.assertEqual(rows[0][7], 'already_matches')

    def test_address_mismatch_continuation_is_explicit(self):
        self.fail_address = 0x0811
        code, report, rows = self.run_addresses([0x0811, 0x0813], continue_on_mismatch=True)
        self.assertEqual(code, 1)
        self.assertEqual(report['status'], 'completed_with_mismatches')
        self.assertEqual(report['verified_addresses'], [0x0813])
        self.assertEqual(len(rows), 2)

    def test_address_mode_still_stops_on_communication_error(self):
        self.error_value = 0x67
        code, report, rows = self.run_addresses([0x0811, 0x0813], continue_on_mismatch=True)
        self.assertEqual(code, 2)
        self.assertEqual(self.attempts, [0x67])
        self.assertEqual(report['status'], 'stopped_on_error')

    def test_address_model_classifies_the_full_requested_window(self):
        plans, unsupported = sweep.address_plans(range(0x0740, 0x0840), 0x67)
        self.assertEqual(len(plans), 59)
        self.assertEqual(len(unsupported), 197)
        self.assertTrue(all(plan['target'] % 2 for plan in plans))
        rejected = {entry['target'] for entry in unsupported}
        self.assertTrue({0x07D9, 0x07E1, 0x07E9, 0x07EB}.issubset(rejected))
        with self.assertRaises(ValueError):
            sweep.address_plans([0x0740], 0x67)
        with self.assertRaises(ValueError):
            sweep.address_plans([0x0817, 0x0817], 0x67)


if __name__ == '__main__':
    unittest.main()
