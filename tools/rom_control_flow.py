#!/usr/bin/env python3
"""Generate destination/source cross-references for decoded engine control flow.

Includes taken conditional branches, unconditional branches, calls, long bank
transfers, annotated jump-table entries and interrupt vector pointers. Ordinary
fall-through and stack-dependent return destinations are not invented edges.
"""
import argparse
import collections
import csv
from pathlib import Path

from m7700dis import Ann, Rom, VECTOR_NAMES, walk


def target_status(rom, insns, target):
    if rom.hole_at(target):
        return 'untrusted_dump_hole'
    if not rom.has(target):
        return 'outside_image'
    return 'decoded' if target in insns else 'not_decoded'


def collect_edges(rom, insns, ann):
    edges, unresolved = [], []

    def add(source, target, instruction, operand, kind, via=''):
        edges.append(dict(source=f'{source:06X}', target=f'{target:06X}',
                          instruction=instruction, operand=operand, kind=kind,
                          via=via, status=target_status(rom, insns, target)))

    for pc, inst in sorted(insns.items()):
        if inst.name in ('RTS', 'RTL', 'RTI'):
            unresolved.append((f'{pc:06X}', inst.name, inst.text,
                               'return destination depends on runtime stack'))
            continue
        if inst.flow not in ('branch', 'jump', 'call', 'jump_table', 'call_table'):
            continue
        if inst.flow in ('jump_table', 'call_table'):
            base = inst.ref
            table = ann.tables.get(base)
            if table is None or table[2] % 2 or not rom.has(base, table[2]):
                unresolved.append((f'{pc:06X}', inst.name, inst.text,
                                   'indirect indexed transfer without a bounded readable table'))
                continue
            for offset in range(0, table[2], 2):
                pointer = base + offset
                add(pc, rom.r16(pointer), inst.name, inst.text,
                    'table_call' if inst.flow == 'call_table' else 'table_jump',
                    f'pointer={pointer:06X}; X={offset:02X}')
            continue
        targets = list(inst.targets)
        # The bank-0 walker deliberately omits long targets outside its image.
        if not targets and inst.text.startswith('$') and ',' not in inst.text:
            targets = [int(inst.text[1:], 16)]
        if not targets:
            unresolved.append((f'{pc:06X}', inst.name, inst.text,
                               'indirect transfer requires runtime pointer value'))
        for target in targets:
            add(pc, target, inst.name, inst.text,
                {'branch': 'conditional_branch', 'jump': 'jump', 'call': 'call'}[inst.flow])

    for addr, name in sorted(VECTOR_NAMES.items()):
        if rom.has(addr, 2):
            add(addr, rom.r16(addr), 'VECTOR', name, 'vector_pointer')
    return sorted(edges, key=lambda e: (e['target'], e['source'], e['via'])), unresolved


def write_csv(path, fields, rows):
    with path.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('docs/rom-inventory'))
    parser.add_argument('--target', type=lambda s: int(s.removeprefix('$'), 16),
                        help='print incoming references for one hexadecimal destination')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    ann = Ann.load(root / 'rom/23710-2L904.ann')
    rom = Rom((root / 'rom/23710-2L904_1000-FFFF.bin').read_bytes(), 0x1000)
    rom.holes = ann.holes
    insns, labels = walk(rom, ann.seeds, {a: t[2] for a, t in ann.tables.items()})
    labels.update(ann.labels)
    edges, unresolved = collect_edges(rom, insns, ann)
    if args.target is not None:
        found = [e for e in edges if int(e['target'], 16) == args.target]
        print(f'{args.target:06X} {labels.get(args.target, "")} — {len(found)} incoming references')
        for e in found:
            print(f"  {e['source']} {e['instruction']:6} {e['operand']} {e['via']}")
        return

    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    fields = ['target', 'target_label', 'source', 'source_label', 'instruction',
              'operand', 'kind', 'via', 'status', 'source_bytes']
    write_csv(out / 'control_flow.csv', fields,
              ((e['target'], labels.get(int(e['target'], 16), ''), e['source'],
                labels.get(int(e['source'], 16), ''), e['instruction'], e['operand'],
                e['kind'], e['via'], e['status'],
                rom.data[int(e['source'], 16) - rom.base:
                         int(e['source'], 16) - rom.base +
                         (2 if e['instruction'] == 'VECTOR' else insns[int(e['source'], 16)].size)].hex(' '))
               for e in edges))
    destinations, sources = collections.defaultdict(list), collections.defaultdict(list)
    for edge in edges:
        destinations[edge['target']].append(edge)
        sources[edge['source']].append(edge)
    write_csv(out / 'jump_targets.csv', ['target', 'label', 'status', 'reference_count', 'sources'],
              ((target, labels.get(int(target, 16), ''), group[0]['status'], len(group),
                ' | '.join(f"{e['source']} {e['instruction']}" +
                           (f" ({e['via']})" if e['via'] else '') for e in group))
               for target, group in sorted(destinations.items())))
    write_csv(out / 'jumps_from.csv', ['source', 'instruction', 'operand', 'targets'],
              ((source, group[0]['instruction'], group[0]['operand'],
                ' | '.join(e['target'] + (f" ({e['via']})" if e['via'] else '') for e in group))
               for source, group in sorted(sources.items())))
    write_csv(out / 'dynamic_transfers.csv', ['source', 'instruction', 'operand', 'limitation'], unresolved)
    kinds = collections.Counter(e['kind'] for e in edges)
    lines = [
        '# Jump destination cross-reference', '',
        'Generated from the annotated 23710-2L904 engine ROM; all addresses are hexadecimal.',
        'Six-digit addresses include the bank: `004EF5` is bank 0, `017B08` is bank 1.', '',
        f'**{len(destinations):,} destinations; {len(edges):,} incoming references; '
        f'{len(sources):,} source locations.**', '',
        'Includes taken conditional branches (`BBC`/`BBS` too), `BRA`/`BRL`, jumps, calls,',
        'long bank transfers, all nine entries of the annotated `$CBAB` jump table,',
        'and vector pointers. A vector source is the pointer location, not an executed instruction.',
        'Table edges are possible destinations selected at runtime; they are not all taken together.', '',
        'Does not include ordinary fall-through. Returns depend on the runtime stack;',
        'they are listed separately in [dynamic_transfers.csv](dynamic_transfers.csv).',
        'Missing bank-1 code and the untrusted `$5D40–$623F` region cannot supply outgoing edges.',
        'Decoded source coverage inherits the disassembler’s width-tracking limitations.', '',
        'Files: [every edge](control_flow.csv), [destinations](jump_targets.csv),',
        '[sources](jumps_from.csv). Existing `transfers.csv` is a narrower call/jump inventory.', '',
        'Regenerate: `python3 tools/rom_control_flow.py`.',
        'Query one target: `python3 tools/rom_control_flow.py --target 4EF5`.', '',
        '| Destination | Label | Status | Sources (instruction address + operation) |',
        '|---|---|---|---|',
    ]
    for target, group in sorted(destinations.items()):
        refs = '<br>'.join(f"`{e['source']}` {e['instruction']}" +
                          (f" ({e['via']})" if e['via'] else '') for e in group)
        lines.append(f"| `{target}` | {labels.get(int(target, 16), '')} | {group[0]['status']} | {refs} |")
    (out / 'JUMP_XREFS.md').write_text('\n'.join(lines) + '\n')
    print(f'Wrote {len(edges)} edges to {len(destinations)} destinations from {len(sources)} sources.')
    print('Edge types:', dict(sorted(kinds.items())))
    print(f'Dynamic transfers listed separately: {len(unresolved)}')


if __name__ == '__main__':
    main()
