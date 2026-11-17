#!/usr/bin/env python3
"""Offline structural inventory of the engine ROM; no hardware access.

Uses the existing decoder, including its width-tracking limitations. Literal
references are evidence to inspect, not inferred variable types or data flow.
"""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path

from m7700dis import Ann, Rom, VECTOR_NAMES, walk


def write_csv(path, header, rows):
    with path.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('docs/rom-inventory'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    data = (root / 'rom/23710-2L904_1000-FFFF.bin').read_bytes()
    ann = Ann.load(root / 'rom/23710-2L904.ann')
    rom = Rom(data, 0x1000)
    rom.holes = ann.holes
    insns, labels = walk(rom, ann.seeds,
                         {addr: table[2] for addr, table in ann.tables.items()})
    labels.update(ann.labels)
    out = args.output
    out.mkdir(parents=True, exist_ok=True)

    # Record actual direct transfers, including long calls outside this dump.
    calls = []
    callers = collections.defaultdict(list)
    entries = set()
    for pc, inst in sorted(insns.items()):
        if inst.name not in ('JSR', 'JSL', 'JMP', 'JML'):
            continue
        targets = list(inst.targets)
        if not targets and inst.text.startswith('$') and ',' not in inst.text:
            targets = [int(inst.text[1:], 16)]
        for target in targets:
            status = ('forwarded_dump_hole' if rom.hole_at(target) else
                      'outside_image' if not rom.has(target) else
                      'decoded' if target in insns else 'not_decoded')
            calls.append((f'{pc:04X}', inst.name, f'{target:06X}',
                          labels.get(target, ''), status))
            if inst.name in ('JSR', 'JSL'):
                entries.add(target)
                callers[target].append(pc)
    for addr in VECTOR_NAMES:
        if rom.has(addr, 2):
            entries.add(rom.r16(addr))
    write_csv(out / 'transfers.csv',
              ['pc', 'instruction', 'target', 'label', 'status'], calls)
    write_csv(out / 'entries.csv',
              ['entry', 'label', 'status', 'call_sites', 'annotation'],
              ((f'{addr:06X}', labels.get(addr, ''),
                'forwarded_dump_hole' if rom.hole_at(addr) else
                'outside_image' if not rom.has(addr) else
                'decoded' if addr in insns else 'not_decoded',
                ' '.join(f'{p:04X}' for p in callers[addr]),
                ' '.join(ann.heads.get(addr, []))) for addr in sorted(entries)))

    refs = collections.defaultdict(list)
    for pc, inst in sorted(insns.items()):
        if inst.ref is not None:
            refs[inst.ref].append((pc, inst.name, inst.text))
    write_csv(out / 'literal_memory_refs.csv',
              ['operand_address', 'name', 'description', 'pc', 'instruction', 'operand'],
              ((f'{addr:04X}', ann.ram.get(addr, ''), ann.ram_desc.get(addr, ''),
                f'{pc:04X}', name, operand)
               for addr in sorted(refs) for pc, name, operand in refs[addr]))
    write_csv(out / 'config_refs.csv',
              ['config_address', 'image_byte', 'pc', 'instruction', 'operand'],
              ((f'{addr:04X}', f'{rom.r8(addr):02X}', f'{pc:04X}', name, operand)
               for addr in range(0x1200, 0x1220) for pc, name, operand in refs[addr]))

    active = []
    for test in range(0x80, 0xAE):
        address = 0x1160 + 2 * (test - 0x80)
        mask, control = rom.r8(address), rom.r8(address + 1)
        supported = (mask, control) != (255, 255)
        group = min(control >> 4, 5)
        slot = (control & 0x7F) >> 1
        active.append((f'{test:02X}', f'{address:04X}', f'{mask:02X}',
                       f'{control:02X}', supported,
                       f'{0x07AC + group:04X}' if supported else '',
                       f'{0x07B7 + group:04X}' if supported else '',
                       f'{0x076F + slot:04X}' if supported else '',
                       bool(control & 1) if supported else ''))
    write_csv(out / 'active_tests.csv',
              ['test', 'descriptor_address', 'mask', 'control', 'supported',
               'requested_flag_byte', 'active_flag_byte', 'value_address', 'takes_value'], active)
    write_csv(out / 'dtc_slots.csv', ['slot', 'consult_code', 'pcode', 'counter_pointer'],
              ((f'{slot:02X}', f'{rom.r8(0x9E0E + slot):02X}',
                ('P' + ''.join(f'{rom.r8(0xE086 + 2 * slot + j):02X}' for j in (0, 1)))
                if rom.r16(0xE086 + 2 * slot) else '',
                f'{rom.r16(0xE1C6 + 2 * slot):04X}') for slot in range(152)))
    groups = [(0x4C7E, 0x4C82, '04', 'odd scheduler slots'),
              (0x4C8E, 0x4CD6, '10', 'slots 1 and 6'),
              (0x4CE6, 0x4D6B, '40', 'REF-event armed; conditional bank paths'),
              (0x4D7D, 0x4E36, '20', 'slots 3 and 8; some calls conditional')]
    write_csv(out / 'scheduled_calls.csv',
              ['group_bit', 'trigger', 'call_pc', 'target', 'label', 'status'],
              ((bit, trigger, pc, target, label, status)
               for start, end, bit, trigger in groups
               for pc, name, target, label, status in calls
               if start <= int(pc, 16) < end and name in ('JSR', 'JSL')))

    # Only the unambiguous adjacent LDA-immediate / diagnostic-call pattern.
    # Other paths compute, pass, or retain the slot and need manual data flow.
    diagnostic_calls = []
    by_end = {pc + inst.size: inst for pc, inst in insns.items()}
    for pc, inst in sorted(insns.items()):
        if inst.name not in ('JSR', 'JSL') or not any(
                target in (0xDE86, 0xD371) for target in inst.targets):
            continue
        previous = by_end.get(pc)
        slot = None
        if previous and previous.name == 'LDA' and previous.text.startswith('#$'):
            slot = int(previous.text[2:], 16)
        valid = slot is not None and slot < 152
        diagnostic_calls.append((f'{pc:04X}', labels.get(inst.targets[0], ''),
                                 f'{slot:02X}' if valid else '',
                                 'P' + ''.join(f'{rom.r8(0xE086 + 2 * slot + j):02X}'
                                               for j in (0, 1)) if valid else '',
                                 'adjacent_constant' if valid else 'requires_data_flow'))
    write_csv(out / 'dtc_call_sites.csv',
              ['call_pc', 'routine', 'slot', 'pcode', 'evidence'], diagnostic_calls)

    # Exhaustive byte accounting: undecoded bytes are not automatically data.
    kinds = ['unclassified'] * len(data)
    for addr, (_, _, size) in ann.tables.items():
        for a in range(addr, addr + size):
            if rom.base <= a < rom.end:
                kinds[a - rom.base] = 'annotated_table'
    for pc, inst in insns.items():
        for a in range(pc, pc + inst.size):
            kinds[a - rom.base] = 'decoded_instruction'
    for start, end, _ in rom.holes:
        for a in range(start, end):
            kinds[a - rom.base] = 'untrusted_dump_hole'
    ranges = []
    start = 0
    for stop in range(1, len(kinds) + 1):
        if stop == len(kinds) or kinds[stop] != kinds[start]:
            ranges.append((f'{rom.base + start:04X}', f'{rom.base + stop - 1:04X}',
                           stop - start, kinds[start]))
            start = stop
    write_csv(out / 'byte_ranges.csv', ['start', 'end_inclusive', 'bytes', 'classification'], ranges)

    # Check branch/call destinations against instruction boundaries. This is a
    # decoder-quality indicator, not proof that all other decodes are correct.
    conflicts = []
    for pc, inst in sorted(insns.items()):
        for target in inst.targets:
            if rom.has(target) and target not in insns:
                conflicts.append((f'{pc:04X}', f'{target:04X}', 'target_not_decoded'))
    occupied = {}
    for pc, inst in sorted(insns.items()):
        for addr in range(pc, pc + inst.size):
            if addr in occupied:
                conflicts.append((f'{pc:04X}', f'{occupied[addr]:04X}', f'overlap_at_{addr:04X}'))
            occupied[addr] = pc
    write_csv(out / 'decoder_checks.csv', ['pc', 'other_pc', 'issue'], conflicts)
    summary = {
        'sha256': hashlib.sha256(data).hexdigest(),
        'image_bytes': len(data), 'decoded_instructions': len(insns),
        'byte_classifications': dict(collections.Counter(kinds)),
        'entry_count': len(entries),
        'outside_image_entries': [f'{a:06X}' for a in sorted(entries) if not rom.has(a) and not rom.hole_at(a)],
        'decoder_check_issues': len(conflicts),
        'limitations': [
            'Structural inventory, not a complete semantic decompilation.',
            'Decoder uses first-path m/x widths and assumes calls preserve widths.',
            'Literal memory refs omit computed pointers and immediate pointer constants.',
            'Indexed operands identify a base, not each effective address.',
            'Named entries can be internal shared tails; entries are not proven function boundaries.',
            'Unclassified bytes can contain data, padding, or missed code.',
        ],
    }
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
