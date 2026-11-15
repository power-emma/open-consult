#!/usr/bin/env python3
"""Sanity-check a m7700dis.py listing: every branch/jump/call target must land on an
instruction boundary. A target in the middle of an instruction means the decoder
mis-sized something earlier (usually an m/x flag mis-track), so the rest of that block
is wrong. See the KNOWN MIS-DECODES note in m7700dis.py; the fix is a `code ADDR m x`
seed in the .ann.

    python3 tools/check_targets.py rom/23710-2L904.asm

Exits non-zero if any target is off-boundary, ignoring targets below the image base
(external/RAM) and inside declared holes (printed as data, never disassembled).
"""
import re
import sys


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: check_targets.py LISTING.asm")
    lines = open(sys.argv[1], encoding="utf-8").read().splitlines()
    addr_re = re.compile(r"^\s{4}([0-9A-F]{4})  ")
    hole_re = re.compile(r"; \$([0-9A-F]{4})-\$([0-9A-F]{4}): NOT REAL ROM")

    starts, datalines, holes, base = set(), set(), [], None
    for line in lines:
        h = hole_re.search(line)
        if h:
            holes.append((int(h.group(1), 16), int(h.group(2), 16)))
        m = addr_re.match(line)
        if not m:
            continue
        a = int(m.group(1), 16)
        base = a if base is None else min(base, a)
        (datalines if ".db " in line else starts).add(a)

    def in_hole(a):
        return any(lo <= a <= hi for lo, hi in holes)

    refs = {int(t, 16) for line in lines for t in re.findall(r"L_([0-9A-F]{4})", line)}
    bad = [a for a in sorted(refs)
           if a not in starts and a >= (base or 0) and a not in datalines and not in_hole(a)]

    print(f"{len(starts)} instruction starts, {len(refs)} targets, {len(bad)} off-boundary")
    for a in bad:
        print(f"  L_{a:04X} lands mid-instruction or in data (likely a flag mis-track "
              f"earlier; add a `code {a:04X} m x` seed)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
