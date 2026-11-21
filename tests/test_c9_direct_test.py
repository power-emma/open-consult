"""Offline model and live-trial verification contract; no serial hardware."""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'write-access/tools'))
import c9_direct_test as trial
from consult.experimental import MutationUnverified
from consult.protocol import ConsultError
from trace_ram_write import HiddenRoutine, direct_payload


class DirectWriteModelTests(unittest.TestCase):
    def test_every_byte_value_at_0817_executes_from_rom(self):
        for value in range(256):
            with self.subTest(value=value):
                model = HiddenRoutine(direct_payload(0x0817, value),
                                      {0x0817: 0xA5, 0x0818: 0x5A, 0x029E: 0xFF}).run()
                self.assertEqual(model.mem[0x0817], value)
                self.assertEqual(model.mem[0x0818], 0x0E)
                writes = [event for event in model.stores if event.address == 0x0817]
                self.assertEqual(len(writes), 1)
                self.assertEqual((writes[0].pc, writes[0].iteration, writes[0].width),
                                 (0x54A0, 16, 2))
                self.assertEqual(model.mem[0x0800:0x0802], bytes([15, 16]))

    def test_bad_alias_or_invalid_target_is_rejected_before_io(self):
        for target in (0x0740, 0x0816, 0x0841):
            with self.subTest(target=target), self.assertRaises(ValueError):
                trial.plan_test(target, 0x42)
        with self.assertRaises(ValueError):
            trial.plan_test(0x07E1, 0x42)  # count increment aliases desired byte


class LiveTrialContractTests(unittest.TestCase):
    def setUp(self):
        self.plan = trial.plan_test(0x0817, 0x42)
        self.client = Mock()
        self.client.init.return_value = (1, 0.1, b'', 0xED)
        self.client.part_number.return_value = (b'', '23710-2L904')
        self.after = False
        self.return_target = 0x42
        self.return_companion = 0x0E
        self.rpm = 0

        def read(addresses):
            if addresses == [0x0995, 0x0994]:
                return self.rpm.to_bytes(2, 'big')
            return bytes(self.return_target if self.after and a == 0x0817 else
                         self.return_companion if self.after and a == 0x0818 else
                         0 for a in addresses)
        self.client.read_memory.side_effect = read

    def mutate(self, *args, **kwargs):
        self.after = True
        return [bytes([0x42]) * 17]

    def test_one_attempt_and_independent_post_stop_readbacks(self):
        report = {}
        with patch.object(trial, 'mutation_stream', side_effect=self.mutate) as mutation:
            self.assertTrue(trial.run_trial(self.client, self.plan, report))
        mutation.assert_called_once()
        self.assertEqual(mutation.call_args.kwargs, {'frames': 1, 'expected_len': 17})
        self.assertEqual(report['verification'], {'0817': 0x42, '0818': 0x0E})
        self.assertEqual(report['observed_changes']['0817'], {'before': 0, 'after': 0x42})

    def test_frame_bytes_cannot_substitute_for_ram_verification(self):
        self.return_target = 0x93
        with patch.object(trial, 'mutation_stream', side_effect=self.mutate):
            report = {}
            self.assertFalse(trial.run_trial(self.client, self.plan, report))
        self.assertEqual(report['status'], 'readback_mismatch')

    def test_companion_must_match_too(self):
        self.return_companion = 0
        with patch.object(trial, 'mutation_stream', side_effect=self.mutate):
            self.assertFalse(trial.run_trial(self.client, self.plan, {}))

    def test_wrong_ecu_or_running_engine_cannot_mutate(self):
        with patch.object(trial, 'mutation_stream') as mutation:
            self.client.part_number.return_value = (b'', 'other')
            with self.assertRaises(ConsultError):
                trial.run_trial(self.client, self.plan, {})
            self.client.part_number.return_value = (b'', '23710-2L904')
            self.rpm = 80
            with self.assertRaises(ConsultError):
                trial.run_trial(self.client, self.plan, {})
            mutation.assert_not_called()

    def test_mutation_error_has_no_followup_or_retry(self):
        report = {}
        with patch.object(trial, 'mutation_stream', side_effect=MutationUnverified('test')) as mutation:
            with self.assertRaises(MutationUnverified):
                trial.run_trial(self.client, self.plan, report)
        mutation.assert_called_once()
        self.assertEqual(self.client.init.call_count, 1)
        self.assertNotIn('after', report)


if __name__ == '__main__':
    unittest.main()
