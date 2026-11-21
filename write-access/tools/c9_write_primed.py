#!/usr/bin/env python3
"""Write to ECU RAM with single-frame overrun.

The builder at L_9B3F rewrites the target address on EVERY streaming frame,
using whatever value is in $07E7 (c9_sub_value) at that moment.  With the
default 3-frame overrun, frame 0 writes $12 (the initial FIFO value) but
frames 1-2 overwrite it with $FF.  The fix: stream exactly 1 frame so the
frame-0 write sticks.

Primers are counterproductive — they drain the H8 FIFO's $12 before the
overrun can use it.  The 2026-11-16 sweep confirmed this:
  0 primers: frame 0 probe=$12, frames 1-2 clobber to $FF
  1+ primers: frame 0 probe=$00 or $FF (FIFO already consumed)

Sequence (single key cycle):
  1. Init + baseline read
  2. Overrun: 20-address C9 payload, stream 1 frame, stop
  3. Re-init + readback

Usage:
  python3 write-access/tools/c9_write_primed.py --target 0817
  python3 write-access/tools/c9_write_primed.py --target 0817 --overrun-frames 1
  python3 write-access/tools/c9_write_primed.py --target 0817 --sweep-frames 1,2,3
  python3 write-access/tools/c9_write_primed.py --target 0817 --repeat 5
"""
import argparse
import datetime
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from consult.protocol import Consult, ConsultError, ENGINE_IDS
from consult.transport import DEFAULT_DEV, Transport
from consult.experimental import mutation_stream, require_research_ecu
from consult.write import (
    CS_PAYLOAD, FORWARD_LO, FORWARD_HI, RESET_CLEARS,
    compute_payload, region_label,
)

LOG_DIR = os.path.join(ROOT, "logs")
DEFAULT_TARGET = 0x0817
DEFAULT_FILL_ADDR = 0x5E00


def run_single_frame_write(dev, target, fill_addr, overrun_frames, log_path,
                           taps=1):
    """Single key cycle: N overrun taps (back-to-back) -> readback.

    taps=2 (double-tap): the first overrun primes the H8 FIFO, the second
    catches the value.  Each tap is init -> overrun -> stop -> init.
    """
    t = Transport(dev, log_path)
    t.note(f"c9_write_1f target=${target:04X} fill=${fill_addr:04X} "
           f"frames={overrun_frames} taps={taps}")

    try:
        c = Consult(t)
        c.ecu_ids = ENGINE_IDS
        r = c.init()
        if r is None:
            print("  init failed")
            return None
        require_research_ecu(c)

        baseline = c.read_memory([target])[0]
        print(f"  baseline: ${baseline:02X}")

        fill_addrs = [fill_addr] * 15
        payload = compute_payload(target, fill_addrs=fill_addrs)
        payload[19] = target  # probe: read target in the frame

        cmd = b"".join(bytes([0xC9, a >> 8, a & 0xFF]) for a in payload)

        all_tap_data = []
        for tap_i in range(taps):
            if tap_i > 0:
                t.note(f"tap {tap_i+1}/{taps}: re-init for next overrun")
                r2 = c.init()
                if r2 is None:
                    print(f"  tap {tap_i+1}: re-init failed")
                    break
                c._mutation_attempted = False

            frames = mutation_stream(c, cmd, frames=overrun_frames,
                                     expected_len=len(payload))

            if not frames:
                print(f"  tap {tap_i+1}: got 0 frames")
                all_tap_data.append([])
                continue

            frame_data = []
            for f in frames:
                frame_data.append({
                    "h8_18": f[18] if len(f) > 18 else None,
                    "probe": f[19] if len(f) > 19 else None,
                })
            all_tap_data.append(frame_data)

            label = f"  tap {tap_i+1}" if taps > 1 else "  overrun"
            print(f"{label}: {len(frames)} frame(s)")
            for fi, fd in enumerate(frame_data):
                probe = f"${fd['probe']:02X}" if fd['probe'] is not None else "??"
                h8 = f"${fd['h8_18']:02X}" if fd['h8_18'] is not None else "??"
                print(f"    frame {fi}: probe={probe} h8[18]={h8}")

        r3 = c.init()
        readback = None
        if r3:
            readback = c.read_memory([target])[0]

        last_frames = all_tap_data[-1] if all_tap_data else []
        written = readback if readback is not None else (
            last_frames[0]["probe"] if last_frames else None)
        changed = written is not None and written != baseline

        return {
            "baseline": baseline,
            "readback": readback,
            "written": written,
            "changed": changed,
            "frames": last_frames,
            "all_taps": all_tap_data,
        }

    except (OSError, ValueError, ConsultError) as e:
        print(f"  error: {e}")
        return None
    finally:
        t.close()


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "--target", type=lambda x: int(x, 16), default=DEFAULT_TARGET,
        help=f"target RAM address in hex (default: {DEFAULT_TARGET:04X}, dtc_seen)")
    ap.add_argument(
        "--fill-addr", type=lambda x: int(x, 16), default=DEFAULT_FILL_ADDR,
        help=f"fill address for positions 0-14 (default: {DEFAULT_FILL_ADDR:04X})")
    ap.add_argument(
        "--overrun-frames", type=int, default=1,
        help="frames to stream per overrun tap (default: 1)")
    ap.add_argument(
        "--taps", type=int, default=2,
        help="overrun taps per trial; tap 1 primes, tap 2 writes (default: 2)")
    ap.add_argument(
        "--dev", default=DEFAULT_DEV,
        help=f"serial device (default: {DEFAULT_DEV})")

    mode = ap.add_mutually_exclusive_group()
    mode.add_argument(
        "--sweep-frames", type=str, default=None,
        help="comma-separated overrun frame counts to test (e.g. 1,2,3)")
    mode.add_argument(
        "--repeat", type=int, default=None,
        help="repeat N trials with the same settings (key cycle between each)")
    mode.add_argument(
        "--run", action="store_true", default=True,
        help="single run (default)")

    args = ap.parse_args()
    target = args.target

    if not 0x0740 <= target <= 0x083F:
        ap.error(f"target ${target:04X} outside $0740-$083F")
    if not FORWARD_LO <= args.fill_addr <= FORWARD_HI:
        ap.error(f"fill-addr outside forwarded range")

    lbl = region_label(target) or f"${target:04X}"
    persistent = target not in RESET_CLEARS

    print(f"c9_write_1f: single-frame ECU RAM write")
    print(f"Target: ${target:04X} ({lbl}), persistent: {'YES' if persistent else 'NO'}")
    print(f"Fill: ${args.fill_addr:04X}, overrun frames: {args.overrun_frames}, taps: {args.taps}")
    print()

    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, f"{datetime.date.today()}_c9-write-1f.log")

    if args.sweep_frames:
        counts = [int(x) for x in args.sweep_frames.split(",")]
        print(f"Sweeping overrun frame counts: {counts}")
        print(f"One key cycle per trial")
        print()

        if input("Proceed? [y/N] ").strip().lower() != "y":
            return

        results = []
        for i, n in enumerate(counts):
            print(f"\n[{i+1}/{len(counts)}] overrun_frames={n}")
            print(f"  >>> Key cycle required. Turn key OFF then ON, wait 2 seconds.")
            resp = input("  Ready? [y/N/q] ").strip().lower()
            if resp == "q":
                break
            if resp not in ("y", ""):
                print("  skipped")
                continue

            r = run_single_frame_write(
                args.dev, target, args.fill_addr, n, log_path,
                taps=args.taps)
            if r is None:
                print("  FAILED")
                continue

            tag = f"WROTE ${r['written']:02X}" if r['changed'] else f"no change (${r['written']:02X})"
            print(f"  result: {tag}, readback=${r['readback']:02X}")
            results.append({"overrun_frames": n, **r})

        print(f"\n{'='*60}")
        print(f"FRAME COUNT SWEEP RESULTS")
        print(f"{'='*60}")
        for r in results:
            tag = f"${r['written']:02X}" if r['changed'] else "---"
            f0_probe = r['frames'][0]['probe'] if r['frames'] else None
            f0 = f"${f0_probe:02X}" if f0_probe is not None else "??"
            print(f"  frames={r['overrun_frames']:2d}  wrote={tag:>5s}  rb=${r['readback']:02X}  base=${r['baseline']:02X}  f0_probe={f0}")
        print(f"\nLog: {log_path}")

    elif args.repeat:
        n = args.repeat
        print(f"Repeating {n} trials with {args.overrun_frames} overrun frame(s)")
        print(f"Key cycle between each trial")
        print()

        if input("Proceed? [y/N] ").strip().lower() != "y":
            return

        results = []
        for i in range(n):
            print(f"\n[{i+1}/{n}]")
            if i > 0:
                print(f"  >>> Key cycle required. Turn key OFF then ON, wait 2 seconds.")
            else:
                print(f"  >>> Key ON, engine OFF.")
            resp = input("  Ready? [y/N/q] ").strip().lower()
            if resp == "q":
                break
            if resp not in ("y", ""):
                print("  skipped")
                continue

            r = run_single_frame_write(
                args.dev, target, args.fill_addr, args.overrun_frames, log_path,
                taps=args.taps)
            if r is None:
                print("  FAILED")
                continue

            tag = f"WROTE ${r['written']:02X}" if r['changed'] else f"no change (${r['written']:02X})"
            print(f"  result: {tag}, readback=${r['readback']:02X}")
            results.append(r)

        hits = sum(1 for r in results if r['changed'])
        print(f"\n{'='*60}")
        print(f"REPEAT RESULTS: {hits}/{len(results)} writes confirmed")
        print(f"{'='*60}")
        for i, r in enumerate(results):
            tag = f"${r['written']:02X}" if r['changed'] else "---"
            f0_probe = r['frames'][0]['probe'] if r['frames'] else None
            f0 = f"${f0_probe:02X}" if f0_probe is not None else "??"
            print(f"  trial {i+1}: wrote={tag:>5s}  rb=${r['readback']:02X}  base=${r['baseline']:02X}  f0_probe={f0}")
        print(f"\nLog: {log_path}")

    else:
        print("Single-frame write.")
        print("Run with key ON, engine OFF.")
        if input("Proceed? [y/N] ").strip().lower() != "y":
            return

        r = run_single_frame_write(
            args.dev, target, args.fill_addr, args.overrun_frames, log_path,
            taps=args.taps)
        if r is None:
            print("\nFAILED")
            return

        print(f"\n{'='*60}")
        if r['changed']:
            print(f"WRITE CONFIRMED: ${target:04X} = ${r['baseline']:02X} -> ${r['written']:02X}")
        else:
            print(f"NO CHANGE: ${target:04X} = ${r['readback']:02X}")
        print(f"{'='*60}")
        print(f"\nLog: {log_path}")


if __name__ == "__main__":
    main()
