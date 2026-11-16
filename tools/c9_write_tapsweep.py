#!/usr/bin/env python3
"""Sweep tap counts to find different FIFO drain values.

Each trial: key cycle, then N taps (1 frame each), readback.
Different tap counts land at different H8 FIFO positions = different values.

Usage:
  python3 tools/c9_write_tapsweep.py --target 0817 --taps 1,2,3,4,5,6,7,8,9,10
"""
import argparse, datetime, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from consult.transport import DEFAULT_DEV
from consult.write import RESET_CLEARS, region_label

sys.path.insert(0, os.path.join(ROOT, "tools"))
from c9_write_primed import run_single_frame_write

LOG_DIR = os.path.join(ROOT, "logs")

ap = argparse.ArgumentParser(description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--target", type=lambda x: int(x, 16), default=0x0817)
ap.add_argument("--taps", type=str, default="1,2,3,4,5,6,7,8,9,10")
ap.add_argument("--dev", default=DEFAULT_DEV)
args = ap.parse_args()

counts = [int(x) for x in args.taps.split(",")]
lbl = region_label(args.target) or f"${args.target:04X}"
print(f"Tap count sweep: {counts}")
print(f"Target: ${args.target:04X} ({lbl}), 1 frame per tap")
print(f"Key cycle between each trial. Go fast.")
print()
if input("Proceed? [y/N] ").strip().lower() != "y":
    sys.exit()

os.makedirs(LOG_DIR, exist_ok=True)
log_path = os.path.join(LOG_DIR, f"{datetime.date.today()}_c9-tapsweep.log")

results = []
for i, n in enumerate(counts):
    print(f"\n[{i+1}/{len(counts)}] taps={n}")
    if i == 0:
        print("  >>> Key ON, engine OFF. Go fast.")
    else:
        print("  >>> Key cycle. OFF then ON, go fast.")
    resp = input("  Ready? [y/N/q] ").strip().lower()
    if resp == "q":
        break
    if resp not in ("y", ""):
        continue

    r = run_single_frame_write(args.dev, args.target, 0x5E00, 1, log_path, taps=n)
    if r is None:
        print("  FAILED")
        continue

    rb = r["readback"]
    tag = f"${rb:02X}" if r["changed"] else "---"
    print(f"  wrote={tag}")
    results.append({"taps": n, "readback": rb, "baseline": r["baseline"], "changed": r["changed"]})

print(f"\n{'='*60}")
print(f"TAP SWEEP RESULTS")
print(f"{'='*60}")
values = {}
for r in results:
    rb = r["readback"]
    tag = f"${rb:02X}" if r["changed"] else "---"
    print(f"  taps={r['taps']:2d}  wrote={tag:>5s}  rb=${rb:02X}  base=${r['baseline']:02X}")
    if r["changed"]:
        values[r["taps"]] = rb

print(f"\nDistinct values: {len(set(values.values()))}")
if values:
    for t, v in sorted(values.items()):
        print(f"  taps={t:2d} -> ${v:02X}")
print(f"Log: {log_path}")
