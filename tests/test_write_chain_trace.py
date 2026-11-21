"""Conditional lower-RAM writes and failed direct-reader chain, offline only."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'write-access/tools'))
sys.path.insert(0, str(ROOT / 'tools'))
from trace_consult_parser import ConsultTrace
from trace_write_chain import direct_mode_findings, receive_pending, schedule_case


class WriteChainTraceTests(unittest.TestCase):
    def test_mailbox_order_changes_lower_ram_write_value(self):
        for target in (0x0770, 0x07A0):
            for schedule, expected in (('no_pending_mailbox', 103),
                                       ('mailbox_before_F0', 103),
                                       ('mailbox_after_F0', 0x93)):
                with self.subTest(target=target, schedule=schedule):
                    result = schedule_case(schedule, target)
                    self.assertEqual(result['actual_write'], expected)
                    self.assertEqual(result['writer_pc'], 0x9B5E)
                    self.assertEqual(result['writer_destination'], target)
                    self.assertFalse(result['hardware_reliability_established'])
                    if target == 0x0770:
                        self.assertEqual(result['applied_fuel_alphas_in_model'],
                                         [min(expected, 125)] * 2)

    def test_direct_reader_and_c9_mode_are_not_simultaneous(self):
        result = direct_mode_findings()
        self.assertEqual(result['old_setup_echo_hex'], 'f5 02 fe')
        self.assertEqual(result['accepted_setup_echo_hex'], 'f5 02 82')
        self.assertEqual(result['C9_argc_after_direct_setup_and_20_C9_addresses'], 40)
        self.assertTrue(result['C9_reader_executed_in_C9_frame'])
        self.assertFalse(result['direct_reader_executed_in_C9_frame'])
        self.assertNotEqual(result['pointer_after_conditional_plant'],
                            result['pointer_after_next_direct_setup'])
        self.assertEqual(result['pointer_after_next_direct_setup'], 0x04CA)

    def test_mailbox_without_pending_flag_does_not_replace_source(self):
        trace = ConsultTrace({0x07E7: 0x67})
        trace.cpu.mem[0x021F] = 1
        trace.cpu.mem[0x029E] = 0
        trace.cpu.mem[0x02B6] = 0x93
        trace.cpu.m = 1
        trace.cpu.run(entry=0xC7F5, ranges=((0xC7F5, 0xCBA2),))
        self.assertEqual(trace.cpu.mem[0x07E7], 0x67)
        receive_pending(trace, 0x93)
        self.assertEqual(trace.cpu.mem[0x07E7], 0x93)


if __name__ == '__main__':
    unittest.main()
