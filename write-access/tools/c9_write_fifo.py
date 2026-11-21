#!/usr/bin/env python3
"""Characterize the H8 FIFO by varying fill addresses and measuring the write value.

The write value is determined by the H8's response FIFO, not by position 18.
c9_find_hidden queues 19 H8 requests at F0 time; those responses drain via
mailbox_receive ($C862) -> $07E7 during streaming.  The last response to
arrive before the builder reads $07E7 is the write value.

This tool varies the fill pattern (positions 0-14) across different H8 record
bases and measures what value actually gets written.  One trial per key cycle
(mutation_attempted latch), targeting dtc_seen ($0810-$083F) which is not
actively overwritten by the ECU.

Modes:
  --sweep-base: try 15 different base addresses (all 15 fills at the same base)
  --sweep-spread: try spread fills with varying start offsets
  --patterns: try specific named fill patterns

Usage:
  python3 write-access/tools/c9_write_fifo.py --sweep-base --target 0817
  python3 write-access/tools/c9_write_fifo.py --sweep-spread --target 0817
  python3 write-access/tools/c9_write_fifo.py --patterns uniform,spread,reverse --target 0817
  python3 write-access/tools/c9_write_fifo.py --dry-run --patterns spread
"""
import argparse
import datetime
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from consult.protocol import Consult, ConsultError, ENGINE_IDS
from consult.transport import DEFAULT_DEV, Transport
from consult.experimental import mutation_stream, require_research_ecu
from consult.write import (
    CS_PAYLOAD, FORWARD_LO, FORWARD_HI, RESET_CLEARS,
    compute_payload, spread_fill, simulate_overrun, simulate_builder_write,
    region_label,
)

LOG_DIR = os.path.join(ROOT, "logs")
DEFAULT_TARGET = 0x0817


def uniform_fill(addr, n=15):
    return [addr] * n


def reverse_spread(n=15, base=0x5D40, stride=8):
    return list(reversed(spread_fill(n, base, stride)))


def named_patterns():
    """Generate a dict of named fill patterns to test."""
    patterns = {}

    patterns["uniform_5E00"] = uniform_fill(0x5E00)
    patterns["uniform_5D40"] = uniform_fill(0x5D40)
    patterns["uniform_5D48"] = uniform_fill(0x5D48)
    patterns["uniform_5D80"] = uniform_fill(0x5D80)
    patterns["uniform_6100"] = uniform_fill(0x6100)

    patterns["spread_5D40_s8"] = spread_fill(15, 0x5D40, 8)
    patterns["spread_5D40_s16"] = spread_fill(15, 0x5D40, 16)
    patterns["spread_5E00_s8"] = spread_fill(15, 0x5E00, 8)
    patterns["spread_5F00_s8"] = spread_fill(15, 0x5F00, 8)
    patterns["spread_6000_s8"] = spread_fill(15, 0x6000, 8)

    patterns["reverse_5D40_s8"] = reverse_spread(15, 0x5D40, 8)
    patterns["reverse_5E00_s8"] = reverse_spread(15, 0x5E00, 8)

    # mixed: first 8 from one region, last 7 from another
    patterns["mixed_5D40_5F00"] = (
        uniform_fill(0x5D40, 8) + uniform_fill(0x5F00, 7))
    patterns["mixed_5E00_6100"] = (
        uniform_fill(0x5E00, 8) + uniform_fill(0x6100, 7))

    return patterns


def sweep_base_patterns(start=0x5D40, end=0x623F, step=0x20):
    """Uniform fills at different base addresses."""
    patterns = {}
    addr = start
    while addr <= end and addr <= FORWARD_HI:
        patterns[f"base_{addr:04X}"] = uniform_fill(addr)
        addr += step
    return patterns


def sweep_spread_patterns(n_offsets=16):
    """Spread fills starting from different offsets."""
    patterns = {}
    for i in range(n_offsets):
        base = FORWARD_LO + i * 0x10
        if base > FORWARD_HI - 15 * 8:
            break
        patterns[f"spread_{base:04X}"] = spread_fill(15, base, 8)
    return patterns


def run_trial(dev, target, fill_addrs, label, log_path):
    """One key cycle: init -> overrun with fill_addrs -> 2 frames -> readback."""
    payload = compute_payload(target, fill_addrs=fill_addrs)
    payload[19] = target  # probe

    t = Transport(dev, log_path)
    t.note(f"c9_write_fifo trial {label} target=${target:04X}")

    try:
        c = Consult(t)
        c.ecu_ids = ENGINE_IDS
        r = c.init()
        if r is None:
            return None
        require_research_ecu(c)

        baseline = c.read_memory([target])[0]

        cmd = b"".join(bytes([0xC9, a >> 8, a & 0xFF]) for a in payload)
        frames = mutation_stream(c, cmd, frames=3, expected_len=len(payload))

        if not frames or len(frames) < 2:
            return None

        frame_data = []
        for f in frames:
            frame_data.append({
                "h8_18": f[18] if len(f) > 18 else None,
                "probe": f[19] if len(f) > 19 else None,
                "raw": bytes(f),
            })

        # post-stop readback
        r2 = c.init()
        readback = None
        if r2:
            readback = c.read_memory([target])[0]

        return {
            "baseline": baseline,
            "readback": readback,
            "frames": frame_data,
            "written": readback if readback is not None else frame_data[1]["probe"],
        }

    except (OSError, ValueError, ConsultError) as e:
        print(f"    error: {e}")
        return None
    finally:
        t.close()


def run_dry(target, patterns):
    """Simulate all patterns and show predicted overrun state."""
    print(f"=== Dry run: {len(patterns)} fill patterns, target ${target:04X} ===\n")

    for name, fill in patterns.items():
        payload = compute_payload(target, fill_addrs=fill)
        ram, stores = simulate_overrun(payload)
        write = simulate_builder_write(ram)

        fill_desc = f"${fill[0]:04X}"
        if len(set(fill)) == 1:
            fill_desc += f" x15"
        elif fill == sorted(fill):
            fill_desc += f"..${fill[-1]:04X} (asc)"
        else:
            fill_desc += f"..${fill[-1]:04X}"

        status = "SKIP" if write is None else f"-> ${write['target']:04X}"
        print(f"  {name:30s}  fill={fill_desc:28s}  {status}")

    print(f"\nOverrun state is identical for all fills (positions 15-18 are fixed).")
    print(f"The write value depends on H8 FIFO content, determined at runtime.")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "--target", type=lambda x: int(x, 16), default=DEFAULT_TARGET,
        help=f"target RAM address in hex (default: {DEFAULT_TARGET:04X}, dtc_seen)")
    ap.add_argument(
        "--dev", default=DEFAULT_DEV,
        help=f"serial device (default: {DEFAULT_DEV})")
    ap.add_argument(
        "--step", type=lambda x: int(x, 16), default=None,
        help="step between addresses for --sweep-base in hex (default: 20, or 8 for small ranges)")
    ap.add_argument(
        "--dry-run", action="store_true",
        help="simulate only")

    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--sweep-base", nargs="?", const="5D40-623F", metavar="START-END",
        help="uniform fills at different base addresses (default: 5D40-623F, e.g. 6000-623F)")
    mode.add_argument(
        "--sweep-spread", action="store_true",
        help="spread fills with varying start offsets")
    mode.add_argument(
        "--patterns", type=str, default=None,
        help="comma-separated named patterns (or 'all' for everything)")

    args = ap.parse_args()
    target = args.target

    if not 0x0740 <= target <= 0x083F:
        ap.error(f"target ${target:04X} outside $0740-$083F")

    if args.sweep_base is not None:
        parts = args.sweep_base.split("-")
        start = int(parts[0], 16)
        end = int(parts[1], 16) if len(parts) > 1 else start + 0x200
        span = end - start
        step = args.step or (0x08 if span <= 0x80 else 0x20)
        patterns = sweep_base_patterns(start, end, step)
    elif args.sweep_spread:
        patterns = sweep_spread_patterns()
    else:
        all_named = named_patterns()
        if args.patterns == "all":
            patterns = all_named
        else:
            names = [n.strip() for n in args.patterns.split(",")]
            patterns = {}
            for n in names:
                if n in all_named:
                    patterns[n] = all_named[n]
                else:
                    ap.error(f"unknown pattern '{n}'; "
                             f"available: {', '.join(sorted(all_named))}")

    lbl = region_label(target) or f"${target:04X}"
    persistent = target not in RESET_CLEARS

    print(f"c9_write_fifo: H8 FIFO characterization via fill pattern variation")
    print(f"Target: ${target:04X} ({lbl}), persistent: {'YES' if persistent else 'NO'}")
    print(f"Patterns to test: {len(patterns)}")
    print(f"One key cycle per trial (requires key off/on between trials)")
    print()

    if args.dry_run:
        run_dry(target, patterns)
        return

    if not persistent:
        print(f"WARNING: ${target:04X} is cleared by consult_reset.")
        print(f"  Post-stop readback will not show the written value.")
        print(f"  Use in-stream probe (frame[19]) instead.")
        print()

    if input("Proceed? [y/N] ").strip().lower() != "y":
        return

    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, f"{datetime.date.today()}_c9-fifo.log")
    out_path = os.path.join(LOG_DIR, f"{datetime.date.today()}_c9-fifo.txt")

    results = []
    value_map = {}

    for i, (name, fill) in enumerate(patterns.items()):
        fill_desc = f"${fill[0]:04X}"
        if len(set(fill)) == 1:
            fill_desc += " x15"

        print(f"\n[{i+1}/{len(patterns)}] {name} (fill={fill_desc})")
        print(f"  >>> Key cycle required. Turn key OFF then ON, wait 2 seconds.")
        if input("  Ready? [y/N/q] ").strip().lower() not in ("y", ""):
            print("  skipped")
            continue

        r = run_trial(args.dev, target, fill, name, log_path)
        if r is None:
            print(f"  FAILED")
            continue

        written = r["written"]
        changed = written is not None and written != r["baseline"]
        h8_18 = r["frames"][0]["h8_18"] if r["frames"] else None

        h8_str = f"h8[18]=${h8_18:02X}" if h8_18 is not None else "h8=??"
        rb_str = f"rb=${r['readback']:02X}" if r['readback'] is not None else "rb=??"
        base_str = f"base=${r['baseline']:02X}"

        if changed:
            print(f"  WROTE ${written:02X}  ({base_str} -> {rb_str}, {h8_str})")
            if written not in value_map:
                value_map[written] = name
        else:
            print(f"  no change ({base_str}, {rb_str}, {h8_str})")

        # show frame details
        for fi, fd in enumerate(r["frames"]):
            probe = fd["probe"]
            h8 = fd["h8_18"]
            p_str = f"${probe:02X}" if probe is not None else "??"
            h_str = f"${h8:02X}" if h8 is not None else "??"
            print(f"    frame {fi}: probe={p_str} h8[18]={h_str}")

        results.append({
            "name": name,
            "fill_0": fill[0],
            "fill_type": "uniform" if len(set(fill)) == 1 else "spread",
            "baseline": r["baseline"],
            "readback": r["readback"],
            "written": written,
            "changed": changed,
            "h8_18": h8_18,
            "frame_probes": [fd["probe"] for fd in r["frames"]],
        })

    # Summary
    print(f"\n{'='*70}")
    print(f"FIFO CHARACTERIZATION RESULTS")
    print(f"{'='*70}")

    print(f"\n{'name':32s} {'fill[0]':>8s} {'type':>8s} {'base':>5s} {'wrote':>6s} {'h8[18]':>7s}")
    print("-" * 70)
    for r in results:
        wrote = f"${r['written']:02X}" if r['changed'] else "---"
        h8 = f"${r['h8_18']:02X}" if r['h8_18'] is not None else "??"
        print(f"  {r['name']:30s} ${r['fill_0']:04X}   {r['fill_type']:>8s} "
              f"${r['baseline']:02X}  {wrote:>5s}  {h8:>5s}")

    if value_map:
        print(f"\nDistinct values written: {len(value_map)}")
        for val in sorted(value_map):
            print(f"  ${val:02X} <- {value_map[val]}")
    else:
        print(f"\nNo value changes observed.")

    # Save
    with open(out_path, "w") as f:
        f.write(f"# c9_write_fifo results {datetime.date.today()}\n")
        f.write(f"# target=${target:04X}\n")
        f.write(f"# name fill_0 fill_type baseline readback written changed h8_18\n")
        for r in results:
            f.write(f"{r['name']} "
                    f"${r['fill_0']:04X} {r['fill_type']} "
                    f"${r['baseline']:02X} "
                    f"${r['readback']:02X} "
                    f"${r['written']:02X} "
                    f"{'Y' if r['changed'] else 'N'} "
                    f"${r['h8_18']:02X}\n")
        if value_map:
            f.write(f"\n# value_map\n")
            for val in sorted(value_map):
                f.write(f"${val:02X} <- {value_map[val]}\n")
    print(f"\nResults: {out_path}")
    print(f"Log: {log_path}")


if __name__ == "__main__":
    main()
