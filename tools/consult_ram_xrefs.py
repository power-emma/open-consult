#!/usr/bin/env python3
"""List literal operand references into the downstream Consult write window.

Offline only. This is a textual index, not CPU data-flow analysis: indexed
operands name their base, immediate operands can be pointers or constants,
and accesses through computed pointers are not attributed to individual bytes.
Operand widths are not inferred; a word access can also touch the next byte.
"""
import csv
from pathlib import Path
import re
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    refs = {a: [] for a in range(0x0740, 0x0840)}
    instruction = re.compile(
        r"^\s+([0-9A-F]{4})\s+(?:[0-9A-F]{2} )+\s+([A-Z][A-Z0-9]*)\s+(.*)"
    )
    for line_no, line in enumerate(
        (root / "rom/23710-2L904.asm").read_text().splitlines(), 1
    ):
        match = instruction.match(line)
        if not match:
            continue
        pc, mnemonic, tail = match.groups()
        operand = tail.split(";", 1)[0].strip()
        for address in re.finditer(r"\$([0-9A-F]{4})(?![0-9A-F])", operand):
            addr = int(address.group(1), 16)
            if addr not in refs:
                continue
            kind = "immediate" if operand[:address.start()].endswith("#") else "memory"
            refs[addr].append(
                f"{pc} {mnemonic} {operand} [{kind}; asm:{line_no}]"
            )
    writer = csv.writer(sys.stdout)
    writer.writerow(["ram_address", "literal_reference_count", "references"])
    for addr, entries in refs.items():
        writer.writerow([f"{addr:04X}", len(entries), " | ".join(entries)])


if __name__ == "__main__":
    main()
