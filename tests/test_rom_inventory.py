"""Regression checks for jump-table bounds and the engine decode inventory."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from m7700dis import Ann, Rom, decode, walk
from rom_control_flow import collect_edges


class ControlFlowReferences(unittest.TestCase):
    def test_branches_long_calls_tables_and_dynamic_transfers(self):
        data = bytearray(0x80)
        data[0:14] = bytes.fromhex('d0 fe 80 fc 22 00 00 01 7c 20 10 6b 00 00')
        data[0x10:0x13] = bytes.fromhex('6c 30 10')  # JMP ($1030), unresolved
        data[0x20:0x24] = bytes.fromhex('40 10 50 10')
        rom = Rom(data, 0x1000)
        ann = Ann()
        ann.tables[0x1020] = ('test_table', '', 4)
        insns = {pc: decode(rom, pc, 0, 0)
                 for pc in (0x1000, 0x1002, 0x1004, 0x1008, 0x100B, 0x1010)}
        edges, dynamic = collect_edges(rom, insns, ann)
        self.assertEqual({(e['source'], e['target'], e['kind']) for e in edges}, {
            ('001000', '001000', 'conditional_branch'),
            ('001002', '001000', 'jump'),
            ('001004', '010000', 'call'),
            ('001008', '001040', 'table_jump'),
            ('001008', '001050', 'table_jump'),
        })
        self.assertEqual({row[0] for row in dynamic}, {'00100B', '001010'})
        table_edges = [e for e in edges if e['kind'] == 'table_jump']
        self.assertEqual({e['via'] for e in table_edges},
                         {'pointer=001020; X=00', 'pointer=001022; X=02'})

    def test_vectors_are_pointer_sources_even_for_missing_targets(self):
        data = bytearray(2)
        data[:] = bytes.fromhex('75 3d')
        edges, _ = collect_edges(Rom(data, 0xFFFE), {}, Ann())
        self.assertEqual(len(edges), 1)
        self.assertEqual((edges[0]['source'], edges[0]['target'], edges[0]['kind']),
                         ('00FFFE', '003D75', 'vector_pointer'))
        self.assertEqual(edges[0]['status'], 'outside_image')


class JumpTableBounds(unittest.TestCase):
    def test_adjacent_valid_pointer_is_not_an_extra_entry(self):
        data = bytearray(0x80)
        data[0:3] = bytes.fromhex('7c 20 10')  # JMP ($1020,X)
        data[0x20:0x24] = bytes.fromhex('40 10 50 10')
        data[0x40] = data[0x50] = 0x6B  # RTL
        rom = Rom(data, 0x1000)
        insns, _ = walk(rom, {0x1000: (0, 0)}, {0x1020: 2})
        self.assertIn(0x1040, insns)
        self.assertNotIn(0x1050, insns)

    def test_engine_decode_has_no_overlapping_instructions(self):
        ann = Ann.load(ROOT / 'rom/23710-2L904.ann')
        rom = Rom((ROOT / 'rom/23710-2L904_1000-FFFF.bin').read_bytes(), 0x1000)
        rom.holes = ann.holes
        insns, _ = walk(rom, ann.seeds, {a: t[2] for a, t in ann.tables.items()})
        occupied = set()
        for pc, inst in sorted(insns.items()):
            span = set(range(pc, pc + inst.size))
            self.assertFalse(occupied & span, f'overlapping instruction at {pc:04X}')
            self.assertTrue(rom.has(pc, inst.size))
            occupied.update(span)
        self.assertNotIn(0x2020, insns)  # used to be a spurious jump-table target
        self.assertNotIn(0x5F1B, insns)  # forwarded dump hole is not code evidence


if __name__ == '__main__':
    unittest.main()
