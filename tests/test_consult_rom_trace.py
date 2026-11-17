"""Selected actual-ROM parser/override paths, not engine or timing emulation."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from consult.protocol import expected_echo
from fuel_control_test import ADDRESSES, build_command
from laptop_fuel import telemetry_command
from trace_consult_parser import ConsultTrace, trace_fuel_request


class ConsultRomTraceTests(unittest.TestCase):
    def test_native_fuel_and_telemetry_for_every_supported_percentage(self):
        for percent in range(75, 126):
            with self.subTest(percent=percent):
                result = trace_fuel_request(percent)
                self.assertEqual(bytes.fromhex(result['echo_hex']), expected_echo(build_command(percent)))
                self.assertEqual(result['parsed']['argc'], 26)
                self.assertEqual(result['parsed']['active_flags'], 2)
                self.assertEqual(result['parsed']['forwarded_count'], 0)
                self.assertEqual(result['applied'], {'alpha_a': percent, 'alpha_b': percent})
                payload = bytes.fromhex(result['telemetry_payload_hex'])
                self.assertEqual(len(payload), len(ADDRESSES))
                self.assertEqual(payload[4:6], bytes([percent, percent]))
                self.assertEqual(payload[10:12], bytes([2, percent]))
                self.assertEqual(result['stop_echo_hex'], 'cf')
                self.assertEqual(result['active_flags_after_stop'], 0)

    def test_native_handler_clamps_raw_parameter_at_both_bounds(self):
        for value, expected in ((0, 75), (74, 75), (126, 125), (255, 125)):
            trace = ConsultTrace()
            trace.send(bytes([0x0A, 0x81, value, 0xF0]))
            trace.apply_native_fuel()
            self.assertEqual(trace.cpu.mem[0x0730:0x0732], bytes([expected, expected]))

    def test_stop_preserves_ready_state_for_next_update(self):
        trace = ConsultTrace()
        for percent in (100, 103, 100):
            self.assertEqual(trace.send(build_command(percent)), expected_echo(build_command(percent)))
            trace.send(b'\xF0')
            trace.apply_native_fuel()
            self.assertEqual(len(trace.build_frame_payload()), 13)
            self.assertEqual(trace.send(b'\x30'), b'\xCF')
            self.assertEqual(trace.cpu.mem[0x071B], 4)
            self.assertEqual(trace.cpu.mem[0x07B7], 0)

    def test_parameter_update_while_streaming_is_rejected_and_clears_test(self):
        trace = ConsultTrace()
        trace.send(build_command(103) + b'\xF0')
        self.assertEqual(trace.send(b'\x0A'), b'\xFE')
        self.assertEqual(trace.cpu.mem[0x07B7], 0)

    def test_test_after_read_list_loses_c9_reply_mode(self):
        trace = ConsultTrace()
        trace.send(telemetry_command() + bytes([0x0A, 0x81, 103, 0xF0]))
        self.assertFalse(trace.cpu.mem[0x071C] & 0x40)
        self.assertEqual(trace.build_frame_payload(), b'')
        self.assertEqual(trace.cpu.mem[0x07B7], 2)

    def test_rejected_idle_target_test_does_not_set_active_flag(self):
        trace = ConsultTrace()
        self.assertEqual(trace.send(b'\x0A\x83'), b'\xF5\xFE')
        self.assertEqual(trace.cpu.mem[0x07B7], 0)


if __name__ == '__main__':
    unittest.main()
