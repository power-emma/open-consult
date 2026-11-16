#!/usr/bin/env python3
"""Calibrate H8 responses in streaming overrun context.

The one-shot sweep (h8_sweep.py) doesn't match streaming behavior because
the H8 auto-increments its read pointer.  With 15x $5E00 fill addresses,
the pointer shifts before position 18 is processed.

This tool runs the actual overrun payload with varying position-18 addresses
and reads back what value the builder actually wrote.  Each trial:
  1. Init, read baseline at target ($076F)
  2. Send 20-addr overrun with position 18 = test address
  3. Read frame[18] (H8 response) and frame[19] (probe = write result)
  4. Post-stop readback to confirm

One trial per init cycle (mutation_attempted latch).  Slow but accurate.

Usage:
  python3 tools/h8_stream_cal.py                     # sweep $5E00-$5EFF
  python3 tools/h8_stream_cal.py --start 5D40 --end 5D80
  python3 tools/h8_stream_cal.py --addrs 5E60,5D48,6118  # specific addresses
"""
import argparse
import datetime
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from consult.protocol import Consult, ConsultError, ENGINE_IDS
from consult.transport import DEFAULT_DEV, Transport
from consult.experimental import mutation_stream, require_research_ecu
from consult.write import FORWARD_LO, FORWARD_HI

LOG_DIR = os.path.join(ROOT, "logs")

TARGET = 0x076F
PROBE_POS = 19


def build_cal_payload(test_addr):
    """Standard overrun payload with test_addr at position 18."""
    main     = 0x5E00
    repair_a = 0x5E0A
    repair_b = 0x5E0B
    tgt_addr = 0x5E2F  # target idx $2F -> $076F
    return [main] * 15 + [repair_a, repair_b, tgt_addr, test_addr, TARGET]


def run_one_trial(dev, test_addr, log_path):
    """Run one overrun with test_addr at position 18, return (h8_response, written_value) or None."""
    t = Transport(dev, log_path)
    t.note(f"h8_stream_cal trial ${test_addr:04X}")

    try:
        c = Consult(t)
        c.ecu_ids = ENGINE_IDS
        r = c.init()
        if r is None:
            print(f"    init failed")
            return None
        _, _, _, ecu = r
        require_research_ecu(c)

        # Baseline
        base = c.read_memory([TARGET])
        baseline = base[0]

        # Fire overrun
        payload = build_cal_payload(test_addr)
        cmd = b"".join(bytes([0xC9, a >> 8, a & 0xFF]) for a in payload)
        frames = mutation_stream(c, cmd, frames=2, expected_len=len(payload))

        if not frames or len(frames) < 2:
            print(f"    got {len(frames)} frame(s), need 2")
            return None

        f0, f1 = frames[0], frames[1]
        h8_resp = f0[18] if len(f0) > 18 else None
        probe_f0 = f0[PROBE_POS] if len(f0) > PROBE_POS else None
        probe_f1 = f1[PROBE_POS] if len(f1) > PROBE_POS else None

        # Post-stop readback
        r2 = c.init()
        readback = None
        if r2:
            rb = c.read_memory([TARGET])
            readback = rb[0]

        return {
            "h8_resp": h8_resp,
            "probe_f0": probe_f0,
            "probe_f1": probe_f1,
            "readback": readback,
            "baseline": baseline,
        }

    except (OSError, ValueError, ConsultError) as e:
        print(f"    error: {e}")
        return None
    finally:
        t.close()


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "--start", type=lambda x: int(x, 16), default=None,
        help="start address in hex (default: 5E00)")
    ap.add_argument(
        "--end", type=lambda x: int(x, 16), default=None,
        help="end address in hex (default: 5EFF)")
    ap.add_argument(
        "--addrs", type=str, default=None,
        help="comma-separated hex addresses to test")
    ap.add_argument(
        "--step", type=int, default=8,
        help="step between addresses in range mode (default: 8, aligned to H8 record boundaries)")
    ap.add_argument(
        "--dev", default=DEFAULT_DEV,
        help=f"serial device (default: {DEFAULT_DEV})")
    args = ap.parse_args()

    if args.addrs:
        test_addrs = [int(a, 16) for a in args.addrs.split(",")]
    else:
        start = args.start or 0x5E00
        end = args.end or 0x5EFF
        test_addrs = list(range(start, end + 1, args.step))

    for a in test_addrs:
        if not FORWARD_LO <= a <= FORWARD_HI:
            ap.error(f"${a:04X} outside forwarded range ${FORWARD_LO:04X}-${FORWARD_HI:04X}")

    print(f"h8_stream_cal: calibrate H8 responses in streaming overrun context")
    print(f"Target: ${TARGET:04X} (at_values[0])")
    print(f"Addresses to test: {len(test_addrs)}")
    print(f"Each trial: init -> overrun -> 2 frames -> stop -> readback")
    print(f"One init cycle per trial (slow but accurate)")
    print()

    if input("Proceed? [y/N] ").strip().lower() != "y":
        return

    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, f"{datetime.date.today()}_h8-stream-cal.log")

    results = []
    value_map = {}  # written_value -> first address that produced it

    for i, addr in enumerate(test_addrs):
        print(f"\n[{i+1}/{len(test_addrs)}] pos 18 = ${addr:04X}...", end="", flush=True)
        r = run_one_trial(args.dev, addr, log_path)
        if r is None:
            print(f" FAILED")
            continue

        written = r["readback"] if r["readback"] is not None else r["probe_f1"]
        changed = written is not None and written != r["baseline"]
        h8 = r["h8_resp"]

        status = ""
        if changed:
            status = f" WROTE ${written:02X}"
            if written not in value_map:
                value_map[written] = addr
        else:
            status = f" no change (baseline=${r['baseline']:02X})"

        h8_str = f"h8[18]=${h8:02X}" if h8 is not None else "h8=??"
        print(f" {h8_str} probe_f1=${r['probe_f1']:02X} rb=${r['readback']:02X}{status}")

        results.append({
            "addr": addr,
            "h8_resp": h8,
            "written": written,
            "changed": changed,
            "baseline": r["baseline"],
        })

    # Summary
    print(f"\n{'='*70}")
    print(f"STREAMING CALIBRATION RESULTS")
    print(f"{'='*70}")

    print(f"\nAddress -> Written value:")
    for r in results:
        if r["changed"]:
            print(f"  ${r['addr']:04X} -> ${r['written']:02X}  (h8[18]=${r['h8_resp']:02X})")

    print(f"\nVALUE LOOKUP TABLE (streaming mode):")
    for val in sorted(value_map):
        print(f"  ${val:02X} -> ${value_map[val]:04X}")

    print(f"\nDistinct writable values: {len(value_map)}")

    # Save results
    out_path = os.path.join(LOG_DIR, f"{datetime.date.today()}_h8-stream-cal.txt")
    with open(out_path, "w") as f:
        f.write(f"# h8_stream_cal results\n")
        f.write(f"# addr h8_resp written changed baseline\n")
        for r in results:
            f.write(f"${r['addr']:04X} "
                    f"${r['h8_resp']:02X} "
                    f"${r['written']:02X} "
                    f"{'Y' if r['changed'] else 'N'} "
                    f"${r['baseline']:02X}\n")
        f.write(f"\n# value_map\n")
        for val in sorted(value_map):
            f.write(f"${val:02X} -> ${value_map[val]:04X}\n")
    print(f"\nResults: {out_path}")
    print(f"Log: {log_path}")


if __name__ == "__main__":
    main()
