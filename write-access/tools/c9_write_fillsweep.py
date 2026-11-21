#!/usr/bin/env python3
"""Sweep fill addresses to find different write values.

Double-tap, 1 frame each, varies fill addr across H8 record bases.
One key cycle per trial.

Usage:
  python3 write-access/tools/c9_write_fillsweep.py --target 0817
"""
import argparse
import datetime
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from consult.transport import DEFAULT_DEV
from consult.write import FORWARD_LO, FORWARD_HI, RESET_CLEARS, region_label

sys.path.insert(0, os.path.join(ROOT, "tools"))
from c9_write_primed import run_single_frame_write

LOG_DIR = os.path.join(ROOT, "logs")

FILL_ADDRS = [
    0x5E00,  # control — known $93
    0x5D40, 0x5D80, 0x5DC0, 0x5E40, 0x5E80, 0x5EC0,
    0x5F00, 0x5F40, 0x5F80, 0x5FC0, 0x6000, 0x6040, 0x6080,
    0x60C0, 0x6100, 0x6140, 0x6180, 0x61C0, 0x6200,
]



def main():
    ap = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", type=lambda x: int(x, 16), default=0x0817)
    ap.add_argument("--dev", default=DEFAULT_DEV)
    args = ap.parse_args()

    lbl = region_label(args.target) or f"${args.target:04X}"
    print(f"Fill-address sweep: {len(FILL_ADDRS)} addresses")
    print(f"Target: ${args.target:04X} ({lbl}), double-tap, 1 frame each")
    print(f"Key cycle between each. Go fast after key-on.")
    print()
    if input("Proceed? [y/N] ").strip().lower() != "y":
        return

    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, f"{datetime.date.today()}_c9-fillsweep.log")

    results = []
    for i, fa in enumerate(FILL_ADDRS):
        print(f"\n[{i+1}/{len(FILL_ADDRS)}] fill=${fa:04X}")
        if i == 0:
            print("  >>> Key ON, engine OFF. Go fast.")
        else:
            print("  >>> Key cycle. OFF then ON, go fast.")
        resp = input("  Ready? [y/N/q] ").strip().lower()
        if resp == "q":
            break
        if resp not in ("y", ""):
            continue

        r = run_single_frame_write(args.dev, args.target, fa, 1, log_path, taps=2)
        if r is None:
            print("  FAILED")
            continue

        rb = r["readback"]
        changed = r["changed"]
        tag = f"${rb:02X}" if changed else "---"
        print(f"  wrote={tag}")
        results.append({"fill": fa, **r})

    print(f"\n{'='*60}")
    print(f"FILL SWEEP RESULTS")
    print(f"{'='*60}")
    values_seen = set()
    for r in results:
        rb = r["readback"]
        changed = rb is not None and rb != r["baseline"]
        tag = f"${rb:02X}" if changed else "---"
        print(f"  fill=${r['fill']:04X}  wrote={tag:>5s}  rb=${rb:02X}  base=${r['baseline']:02X}")
        if changed:
            values_seen.add(rb)
    print(f"\nDistinct values written: {len(values_seen)}")
    if values_seen:
        print(f"  {', '.join(f'${v:02X}' for v in sorted(values_seen))}")
    print(f"Log: {log_path}")


if __name__ == "__main__":
    main()
