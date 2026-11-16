#!/usr/bin/env python3
"""Sweep H8 forwarded addresses to characterize responses.

Normal C9 reads of $5D40-$623F are forwarded to the H8 coprocessor.
The H8's response byte becomes the clobber value in the write primitive
(mailbox_receive at $C862 overwrites c9_sub_value before the builder
reads it).  To control the written value, we need an H8 address that
responds with the desired byte.

This tool reads a range of forwarded addresses across multiple passes
to find stable (predictable) responses and build a value lookup table.

Usage:
  python3 tools/h8_sweep.py                          # default: $5E00-$5EFF, 3 passes
  python3 tools/h8_sweep.py --start 5D40 --end 5E40  # custom range
  python3 tools/h8_sweep.py --passes 5               # more passes for stability check
  python3 tools/h8_sweep.py --all                     # full forwarded range (slow)
"""
import argparse
import datetime
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from consult.protocol import Consult, ConsultError, ENGINE_IDS
from consult.transport import DEFAULT_DEV, Transport
from consult.experimental import require_research_ecu

LOG_DIR = os.path.join(ROOT, "logs")
FORWARD_LO = 0x5D40
FORWARD_HI = 0x623F


def sweep_range(c, start, end):
    """Read every address in [start, end] via C9, 8 at a time."""
    results = []
    addrs = list(range(start, end + 1))
    for i in range(0, len(addrs), 8):
        chunk = addrs[i:i + 8]
        data = c.read_memory(chunk)
        results.extend(zip(chunk, data))
    return results


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "--start", type=lambda x: int(x, 16), default=0x5E00,
        help="start address in hex (default: 5E00)")
    ap.add_argument(
        "--end", type=lambda x: int(x, 16), default=0x5EFF,
        help="end address in hex (default: 5EFF)")
    ap.add_argument(
        "--all", action="store_true",
        help="sweep full forwarded range $5D40-$623F")
    ap.add_argument(
        "--passes", type=int, default=3,
        help="number of read passes (default: 3)")
    ap.add_argument(
        "--dev", default=DEFAULT_DEV,
        help=f"serial device (default: {DEFAULT_DEV})")
    args = ap.parse_args()

    if args.all:
        start, end = FORWARD_LO, FORWARD_HI
    else:
        start, end = args.start, args.end

    if not FORWARD_LO <= start <= FORWARD_HI:
        ap.error(f"start ${start:04X} outside forwarded range ${FORWARD_LO:04X}-${FORWARD_HI:04X}")
    if not FORWARD_LO <= end <= FORWARD_HI:
        ap.error(f"end ${end:04X} outside forwarded range ${FORWARD_LO:04X}-${FORWARD_HI:04X}")
    if start > end:
        ap.error("start must be <= end")
    if not 1 <= args.passes <= 20:
        ap.error("passes must be in 1..20")

    n_addrs = end - start + 1
    n_reads = (n_addrs + 7) // 8
    print(f"h8_sweep: characterize H8 responses for value control")
    print(f"Range: ${start:04X}-${end:04X} ({n_addrs} addresses)")
    print(f"Passes: {args.passes}")
    print(f"Reads per pass: {n_reads}")
    print()

    os.makedirs(LOG_DIR, exist_ok=True)
    log = os.path.join(LOG_DIR, f"{datetime.date.today()}_h8-sweep.log")
    t = Transport(args.dev, log)
    t.note(f"h8_sweep ${start:04X}-${end:04X} x{args.passes}")

    try:
        c = Consult(t)
        c.ecu_ids = ENGINE_IDS
        r = c.init()
        if r is None:
            sys.exit("init failed (ignition on?)")
        attempt, secs, _, ecu = r
        require_research_ecu(c)
        print(f"init ok: id {ecu:02X}, attempt {attempt}, {secs*1000:.0f} ms")

        # Collect passes
        all_passes = []
        for p in range(args.passes):
            print(f"\nPass {p+1}/{args.passes}...")
            results = sweep_range(c, start, end)
            all_passes.append(results)
            # Quick progress: show first few
            if p == 0:
                preview = results[:8]
                print(f"  first 8: {' '.join(f'${v:02X}' for _, v in preview)}")

        # Analyze stability
        print(f"\n{'='*70}")
        print(f"ANALYSIS")
        print(f"{'='*70}")

        # Build per-address data
        addr_data = {}
        for addr_idx in range(n_addrs):
            addr = start + addr_idx
            values = [all_passes[p][addr_idx][1] for p in range(args.passes)]
            addr_data[addr] = values

        # Classify: stable (all passes same) vs variable
        stable = {}
        variable = {}
        for addr, values in addr_data.items():
            if len(set(values)) == 1:
                stable[addr] = values[0]
            else:
                variable[addr] = values

        print(f"\nStable addresses: {len(stable)}/{n_addrs}")
        print(f"Variable addresses: {len(variable)}/{n_addrs}")

        # Value coverage from stable addresses
        value_sources = {}
        for addr, val in sorted(stable.items()):
            if val not in value_sources:
                value_sources[val] = addr

        print(f"\nDistinct stable values: {len(value_sources)}/256")

        # Print stable address table (compact)
        if stable:
            print(f"\nStable responses (addr -> value):")
            row = []
            for addr in sorted(stable):
                row.append(f"${addr:04X}=${stable[addr]:02X}")
                if len(row) == 8:
                    print(f"  {' '.join(row)}")
                    row = []
            if row:
                print(f"  {' '.join(row)}")

        # Print value lookup table
        if value_sources:
            print(f"\nVALUE LOOKUP TABLE (value -> first stable H8 address):")
            print(f"  To write byte $XX, use this address at position 18.")
            print()
            for val in sorted(value_sources):
                addr = value_sources[val]
                print(f"  ${val:02X} -> ${addr:04X}")

        # Print variable addresses (brief)
        if variable:
            print(f"\nVariable addresses (values across {args.passes} passes):")
            for addr in sorted(variable):
                vals = variable[addr]
                print(f"  ${addr:04X}: {' '.join(f'${v:02X}' for v in vals)}")

        # Dump raw data for offline analysis
        raw_path = os.path.join(LOG_DIR, f"{datetime.date.today()}_h8-sweep-raw.txt")
        with open(raw_path, "w") as f:
            f.write(f"# h8_sweep ${start:04X}-${end:04X} x{args.passes}\n")
            f.write(f"# addr " + " ".join(f"pass{p}" for p in range(args.passes)) + " stable\n")
            for addr in sorted(addr_data):
                values = addr_data[addr]
                s = "Y" if addr in stable else "N"
                f.write(f"${addr:04X} " + " ".join(f"${v:02X}" for v in values) + f" {s}\n")
        print(f"\nRaw data: {raw_path}")

        # Summary for write primitive
        print(f"\n{'='*70}")
        print(f"WRITE PRIMITIVE STATUS")
        print(f"{'='*70}")
        if len(value_sources) == 0:
            print(f"No stable H8 responses found. Cannot control write value yet.")
            print(f"Try: more passes, different range, or engine-on vs engine-off.")
        elif len(value_sources) < 10:
            print(f"Limited value control: {len(value_sources)} distinct values available.")
            print(f"Can write: {', '.join(f'${v:02X}' for v in sorted(value_sources))}")
        else:
            print(f"Good value coverage: {len(value_sources)}/256 values available.")
            missing = [v for v in range(256) if v not in value_sources]
            if len(missing) <= 20:
                print(f"Missing: {', '.join(f'${v:02X}' for v in missing)}")
            else:
                print(f"Missing {len(missing)} values. Wider sweep may help.")

    except (OSError, ValueError, ConsultError) as e:
        print(f"\nerror: {e}")
    finally:
        t.close()
        print(f"\nlog: {log}")


if __name__ == "__main__":
    main()
