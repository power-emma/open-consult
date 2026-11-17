"""Native fuel-control request and verification checks, without hardware."""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import fuel_control_test as fuel
from consult.protocol import ConsultError, NARGS, expected_echo


def frame(percent=103, bank_b=None, flags=2, value=None):
    return bytes([0, 80, 0, 100, percent, percent if bank_b is None else bank_b,
                  0, 250, 0, 251, flags, percent if value is None else value, 0])


class FuelControlTests(unittest.TestCase):
    def test_packet_is_native_override_then_only_local_reads(self):
        command = fuel.build_command(103)
        self.assertEqual(command[:3], bytes([0x0A, 0x81, 103]))
        self.assertEqual(expected_echo(command)[:3], bytes([0xF5, 0x81, 103]))
        args, pc = 0, 0
        while pc < len(command):
            args += NARGS[command[pc]]
            pc += 1 + NARGS[command[pc]]
        self.assertEqual(args, 28)
        self.assertEqual(pc, len(command))
        self.assertTrue(all(address < 0x1000 for address in fuel.ADDRESSES))
        for bad in (74, 126):
            with self.assertRaises(ValueError):
                fuel.build_command(bad)

    def test_decode_distinguishes_request_from_applied_banks(self):
        self.assertTrue(fuel.decode_sample(frame(), 103)['both_banks_match'])
        self.assertFalse(fuel.decode_sample(frame(bank_b=100), 103)['both_banks_match'])
        self.assertFalse(fuel.decode_sample(frame(flags=0), 103)['both_banks_match'])
        self.assertFalse(fuel.decode_sample(frame(value=100), 103)['both_banks_match'])

    def run_case(self, samples, stop=0xCF, released=0, baseline=b'\x00\x50\x64\x64'):
        client, result = Mock(), {}
        clock = [0.0]
        client.stop.return_value = (stop, b'')

        def read(**kwargs):
            clock[0] += 0.1
            sample = samples.pop(0) if len(samples) > 1 else samples[0]
            return sample

        client.read_frame.side_effect = read
        with patch.object(fuel, 'read_checked', side_effect=[baseline, bytes([released])]):
            verified = fuel.run_step(client, 103, 0.5, result, clock=lambda: clock[0])
        return verified, result, client

    def test_settling_then_three_applied_samples_and_release(self):
        verified, result, client = self.run_case([frame(100), frame(), frame(), frame(), frame()])
        self.assertTrue(verified)
        client.command.assert_called_once_with(fuel.build_command(103), retries=0, mutation=True)
        client.stop.assert_called_once()
        self.assertTrue(result['override_released'])

    def test_one_wrong_bank_is_not_a_verified_tune(self):
        verified, result, _ = self.run_case([frame(bank_b=100)])
        self.assertFalse(verified)
        self.assertFalse(result['both_banks_verified'])

    def test_override_must_clear_after_stop(self):
        verified, result, _ = self.run_case([frame()], released=2)
        self.assertFalse(verified)
        self.assertFalse(result['override_released'])

    def test_missing_stop_ack_is_not_success(self):
        with self.assertRaises(ConsultError):
            self.run_case([frame()], stop=None)

    def test_command_error_stops_and_is_not_retried(self):
        client, result = Mock(), {}
        client.command.side_effect = ConsultError('rejected')
        client.stop.return_value = (0xCF, b'')
        with patch.object(fuel, 'read_checked', return_value=b'\x00\x50\x64\x64'):
            with self.assertRaises(ConsultError):
                fuel.run_step(client, 103, 1, result)
        client.command.assert_called_once()
        client.stop.assert_called_once()

    def test_engine_off_prevents_request(self):
        client, result = Mock(), {}
        with patch.object(fuel, 'read_checked', return_value=b'\x00\x00\x64\x64'):
            with self.assertRaises(ConsultError):
                fuel.run_step(client, 103, 1, result)
        client.command.assert_not_called()


if __name__ == '__main__':
    unittest.main()
