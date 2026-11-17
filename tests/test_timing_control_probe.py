"""Timing capture tests: request-state evidence must not imply angle semantics."""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from consult.protocol import ConsultError, expected_echo
from trace_consult_parser import ConsultTrace
import timing_control_probe as timing


def frame(raw=1, flags=4, reported=100):
    return bytes([0, 80, reported, raw, flags, 10, 60, 60, 0, 0,
                  0, 0, 0, 0, 0, 0, 0, 0, 100])


class TimingRomParserTests(unittest.TestCase):
    def test_native_timing_packet_is_accepted_by_selected_rom_paths(self):
        for raw in (0, 1, 2, 0xFB, 0xFF):
            trace = ConsultTrace({0x0994: 80, 0x0732: 100})
            command = timing.build_command(raw)
            self.assertEqual(trace.send(command), expected_echo(command))
            trace.send(b'\xF0')
            self.assertEqual(trace.cpu.mem[0x07B7], 4)
            self.assertEqual(trace.cpu.mem[0x0771], raw)
            self.assertEqual(trace.cpu.mem[0x073B], 38)
            self.assertEqual(trace.cpu.mem[0x07E1], 0)
            payload = trace.build_frame_payload()
            self.assertEqual(len(payload), 19)
            self.assertEqual(payload[2:5], bytes([100, raw, 4]))
            self.assertEqual(trace.send(b'\x30'), b'\xCF')
            self.assertEqual(trace.cpu.mem[0x07B7], 0)

    def test_passive_command_does_not_request_timing_override(self):
        trace = ConsultTrace({0x0732: 100})
        trace.send(timing.build_command() + b'\xF0')
        self.assertEqual(trace.cpu.mem[0x07B7], 0)
        self.assertEqual(len(trace.build_frame_payload()), 19)


class TimingCaptureTests(unittest.TestCase):
    def capture(self, data, raw=1, ack=0xCF, release=0):
        client, result, clock = Mock(), {}, [0.0]
        client.stop.return_value = ack, b''
        def read(**kwargs):
            clock[0] += 0.1
            return data
        client.read_frame.side_effect = read
        with patch.object(timing, 'read_checked', side_effect=[b'\x00\x50', bytes([release])]):
            timing.capture_stage(client, raw, 0.5, result, clock=lambda: clock[0])
        return result, client

    def test_capture_verifies_state_but_never_claims_degrees_per_byte(self):
        result, client = self.capture(frame())
        self.assertTrue(result['request_state_verified'])
        self.assertTrue(result['override_released'])
        self.assertFalse(result['timing_parameter_semantics_verified'])
        self.assertEqual(result['reported_timing_summary']['median_btdc'], 10)
        client.command.assert_called_once_with(timing.build_command(1), retries=0, mutation=True)

    def test_passive_capture_has_no_changing_command(self):
        result, client = self.capture(frame(raw=0, flags=0), raw=None)
        self.assertEqual(result['kind'], 'normal_control')
        self.assertFalse(client.command.call_args.kwargs['mutation'])

    def test_wrong_parameter_or_missing_flag_is_not_verified(self):
        for data in (frame(raw=2), frame(flags=0)):
            with self.subTest(data=data), self.assertRaises(ConsultError):
                self.capture(data)

    def test_release_and_stop_ack_are_required(self):
        for options in ({'ack': None}, {'release': 4}):
            with self.subTest(options=options), self.assertRaises(ConsultError):
                self.capture(frame(), **options)

    def test_rejection_attempts_cleanup_and_does_not_retry(self):
        client = Mock()
        client.command.side_effect = ConsultError('rejected')
        client.stop.return_value = 0xCF, b''
        with patch.object(timing, 'read_checked', return_value=b'\x00\x50'):
            with self.assertRaises(ConsultError):
                timing.capture_stage(client, 1, 1, {})
        client.command.assert_called_once()
        client.stop.assert_called_once()


if __name__ == '__main__':
    unittest.main()
