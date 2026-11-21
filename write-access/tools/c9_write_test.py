#!/usr/bin/env python3
"""c9_write_test: hardware verification of the downstream write primitive.

Runs three write trials against at_values ($076F-$079C), which persists
through consult_reset and can be verified by independent post-stop readback.

  Trial 1: $A5 -> $076F   value control
  Trial 2: $5A -> $076F   same target, different value (value selectivity)
  Trial 3: $42 -> $0780   different target (target selectivity)

Three passes with distinct target/value pairs establishes the downstream
writer.  Any failure points to the timing hazard (WRITE_PRIMITIVE.md
"Timing concern").

What the test does NOT do:
  - Set actuator flags (no at_active/at_req writes)
  - Activate any test or physical output
  - Write outside at_values

Key on, engine off.  Key cycle clears all state.

Usage:
  python3 write-access/tools/c9_write_test.py --dry-run
  python3 write-access/tools/c9_write_test.py
  python3 write-access/tools/c9_write_test.py --dev /dev/ttyUSB1
"""
import argparse
import datetime
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from consult.protocol import Consult, ConsultError, ENGINE_IDS
from consult.transport import DEFAULT_DEV, Transport
from consult.experimental import mutation_stream, require_research_ecu, MutationUnverified
from consult.write import (
    compute_payload, simulate_write, region_label,
    RESET_CLEARS, C9_SUB_VAL, HIDDEN_N, REPLY_CURSOR, FWD_FLAGS,
)

LOG_DIR = os.path.join(ROOT, "logs")

TRIALS = [
    (0x076F, 0xA5, "at_values[0]: value control"),
    (0x076F, 0x5A, "at_values[0]: value selectivity"),
    (0x0780, 0x42, "at_values[17]: target selectivity"),
]

# Overrun handler state, read after each trial as a sanity check.
OVERRUN_STATE = [
    (HIDDEN_N,     "c9_hidden_n"),
    (REPLY_CURSOR, "reply_cursor"),
    (FWD_FLAGS,    "fwd_flags"),
    (0x07E5,       "idx[$0E]"),
    (C9_SUB_VAL,   "c9_sub_value"),
]

# Canary window around each target to detect collateral writes.
CANARY_RADIUS = 4

N_FRAMES = 3


def read_region(c, start, length):
    """Read a contiguous RAM region, 8 bytes at a time."""
    result = bytearray()
    for i in range(0, length, 8):
        n = min(8, length - i)
        result += c.read_memory(list(range(start + i, start + i + n)))
    return bytes(result)


def read_addrs(c, addrs):
    """Read a list of individual addresses, 8 at a time."""
    result = bytearray()
    for i in range(0, len(addrs), 8):
        result += c.read_memory(addrs[i:i + 8])
    return bytes(result)


def dump_region(data, start, mark_addr=None, mark_val=None):
    """Print a hex dump with optional highlight."""
    parts = []
    for i, b in enumerate(data):
        addr = start + i
        s = f"${b:02X}"
        if addr == mark_addr:
            s = f"[{b:02X}]"
        parts.append(s)
    print(f"    ${start:04X}: {' '.join(parts)}")


def run_dry():
    """Simulate all trials without touching the ECU."""
    print("=== DRY RUN (simulation only) ===\n")
    all_ok = True
    for i, (target, value, desc) in enumerate(TRIALS, 1):
        sim = simulate_write(target, value)
        w = sim["write"]
        ok = w and w["target"] == target and w["value"] == value
        status = "OK" if ok else "FAIL"
        if not ok:
            all_ok = False

        print(f"Trial {i}: ${value:02X} -> ${target:04X} ({desc})")
        print(f"  Simulation: {status}")
        if w:
            print(f"  Predicted:  ${w['value']:02X} -> ${w['target']:04X} "
                  f"(cursor=${w['cursor']:02X}, idx=${w['idx']:02X})")
        else:
            print(f"  Builder would not fire (flags wrong)")

        ram = sim["ram"]
        print(f"  Overrun state: n=${ram.get(HIDDEN_N, 0):02X} "
              f"cursor=${ram.get(REPLY_CURSOR, 0):02X} "
              f"flags=${ram.get(FWD_FLAGS, 0):02X} "
              f"c9_sub_val=${ram.get(C9_SUB_VAL, 0):02X}")
        print(f"  Persistent: {'YES' if target not in RESET_CLEARS else 'NO'}")
        print()

    if all_ok:
        print("All trials simulate correctly.")
        print("Run without --dry-run to test on the ECU.")
    else:
        print("Simulation failures -- do not run on hardware.")
    return all_ok


def run_trial(t, trial_num, target, value, desc):
    """Execute one write trial on the ECU. Returns a result dict."""
    print(f"\n{'=' * 60}")
    print(f"TRIAL {trial_num}: ${value:02X} -> ${target:04X}  ({desc})")
    print(f"{'=' * 60}")

    # Simulate first.
    sim = simulate_write(target, value)
    w = sim["write"]
    if not w or w["target"] != target or w["value"] != value:
        print("  SKIP: simulation predicts wrong outcome")
        return {"status": "skip"}

    # Fresh Consult (mutation latch is per-instance).
    c = Consult(t)
    c.ecu_ids = ENGINE_IDS

    r = c.init()
    if r is None:
        print("  FAIL: init failed (ignition on?)")
        return {"status": "fail", "reason": "init"}
    attempt, secs, _, ecu = r
    require_research_ecu(c)
    t.note(f"trial {trial_num}: ${value:02X} -> ${target:04X}")
    print(f"  Init: id {ecu:02X}, attempt {attempt}, {secs * 1000:.0f} ms")

    # --- Baseline ---
    canary_lo = max(0x076F, target - CANARY_RADIUS)
    canary_hi = min(0x079D, target + CANARY_RADIUS + 1)
    canary_len = canary_hi - canary_lo

    baseline = read_region(c, canary_lo, canary_len)
    target_off = target - canary_lo
    baseline_val = baseline[target_off]

    print(f"  Baseline ${target:04X} = ${baseline_val:02X}")
    dump_region(baseline, canary_lo, mark_addr=target)

    if baseline_val == value:
        print(f"  WARNING: target already contains ${value:02X}")

    # Read overrun state before.
    ov_addrs = [a for a, _ in OVERRUN_STATE]
    ov_before = read_addrs(c, ov_addrs)

    # --- Write ---
    payload = compute_payload(target, value)
    # Replace dummy at position 19 with probe (target is outside forwarded
    # range, so the overrun skips it; reply builder reads it normally).
    payload[19] = target

    cmd = b"".join(bytes([0xC9, a >> 8, a & 0xFF]) for a in payload)

    print(f"  Sending 20 C9 addresses + F0 ({N_FRAMES} frames)...")
    try:
        frames = mutation_stream(
            c, cmd, frames=N_FRAMES, expected_len=len(payload))
    except MutationUnverified as e:
        print(f"  FAIL: {e}")
        t.note(f"trial {trial_num} mutation unverified")
        return {"status": "fail", "reason": str(e)}

    t.note(f"trial {trial_num}: {len(frames)} frames")
    print(f"  Streamed {len(frames)} frame(s)")

    # In-stream probe (position 19 = target RAM value in each frame).
    probe_pos = 19
    print(f"  In-stream probe (${target:04X}):")
    write_seen = False
    for fi, frame in enumerate(frames):
        if len(frame) > probe_pos:
            pv = frame[probe_pos]
            tag = ""
            if pv == value and pv != baseline_val and not write_seen:
                write_seen = True
                tag = " <- WRITE VISIBLE"
            elif fi == 0:
                tag = " (pre-write expected)"
            print(f"    frame {fi}: ${pv:02X}{tag}")
        else:
            print(f"    frame {fi}: (short: {len(frame)} bytes)")

    # --- Post-stop readback ---
    # mutation_stream already called stop().  Re-init for clean reads.
    r = c.init()
    if r is None:
        print("  FAIL: post-stop init failed")
        return {"status": "fail", "reason": "post-stop init"}

    after = read_region(c, canary_lo, canary_len)
    after_val = after[target_off]

    print(f"  Readback ${target:04X} = ${after_val:02X}")
    dump_region(after, canary_lo, mark_addr=target)

    # Overrun state after (sanity check: direct overrun should have fired).
    ov_after = read_addrs(c, ov_addrs)
    ov_changed = any(a != b for a, b in zip(ov_before, ov_after))
    print(f"  Overrun state {'CHANGED' if ov_changed else 'UNCHANGED'}:")
    for j, (addr, name) in enumerate(OVERRUN_STATE):
        b, a = ov_before[j], ov_after[j]
        flag = " *" if b != a else ""
        print(f"    {name:16s} ${addr:04X}: ${b:02X} -> ${a:02X}{flag}")

    # Canary: check for collateral writes outside the target.
    collateral = []
    for i in range(canary_len):
        addr = canary_lo + i
        if addr == target:
            continue
        if baseline[i] != after[i]:
            collateral.append((addr, baseline[i], after[i]))

    if collateral:
        print(f"  COLLATERAL WRITES ({len(collateral)}):")
        for addr, b, a in collateral:
            lbl = region_label(addr) or ""
            print(f"    ${addr:04X}: ${b:02X} -> ${a:02X}  {lbl}")

    # --- Verdict ---
    result = {
        "target": target,
        "value": value,
        "baseline": baseline_val,
        "readback": after_val,
        "write_seen": write_seen,
        "ov_changed": ov_changed,
        "collateral": len(collateral),
    }

    if after_val == value and baseline_val != value:
        print(f"\n  >> PASS: ${target:04X} changed ${baseline_val:02X} -> ${value:02X}")
        result["status"] = "pass"
    elif after_val == value and baseline_val == value:
        print(f"\n  >> INCONCLUSIVE: already had ${value:02X}")
        result["status"] = "inconclusive"
    elif write_seen and after_val != value:
        print(f"\n  >> PARTIAL: probe showed ${value:02X} during streaming, "
              f"readback is ${after_val:02X}")
        result["status"] = "partial"
    else:
        print(f"\n  >> FAIL: readback ${after_val:02X}, "
              f"expected ${value:02X}, baseline ${baseline_val:02X}")
        result["status"] = "fail"

    return result


def run_live(dev):
    """Run all trials on the ECU."""
    os.makedirs(LOG_DIR, exist_ok=True)
    log = os.path.join(
        LOG_DIR,
        f"{datetime.date.today()}_c9-write-test.log")
    t = Transport(dev, log)
    t.note("c9_write_test: downstream write verification")

    results = []
    try:
        # Verify ECU identity once.
        c = Consult(t)
        c.ecu_ids = ENGINE_IDS
        r = c.init()
        if r is None:
            sys.exit("init failed (ignition on?)")
        require_research_ecu(c)
        _, identity = c.part_number()
        print(f"ECU: {identity}")

        # Read full at_values baseline for the record.
        full_baseline = read_region(c, 0x076F, 0x2E)
        print(f"at_values baseline ($076F-$079C):")
        for off in range(0, 0x2E, 16):
            row = full_baseline[off:off + 16]
            cells = " ".join(f"{b:02X}" for b in row)
            print(f"  ${0x076F + off:04X}: {cells}")

        for i, (target, value, desc) in enumerate(TRIALS, 1):
            result = run_trial(t, i, target, value, desc)
            results.append(result)
            t.note(f"trial {i} result: {result.get('status', '?')}")

    except (OSError, ValueError) as e:
        print(f"\nerror: {e}")
        raise SystemExit(1) from e
    finally:
        t.close()

    # --- Summary ---
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")

    passes = 0
    fails = 0
    for i, (r, (target, value, desc)) in enumerate(zip(results, TRIALS), 1):
        status = r.get("status", "?").upper()
        extra = ""
        if r.get("collateral", 0):
            extra = f"  ({r['collateral']} collateral)"
        if r.get("write_seen") and status != "PASS":
            extra += "  (probe saw value during stream)"
        print(f"  Trial {i}: {status:14s}  "
              f"${value:02X} -> ${target:04X}  {desc}{extra}")
        if status == "PASS":
            passes += 1
        elif status in ("FAIL", "PARTIAL"):
            fails += 1

    print()
    if passes == len(TRIALS):
        print("ALL TRIALS PASSED.")
        print("The downstream write primitive is hardware-confirmed.")
        print("Update WRITE_PRIMITIVE.md accordingly.")
    elif passes > 0:
        print(f"{passes}/{len(TRIALS)} passed.  Timing-sensitive -- "
              f"the mechanism works but is not reliable.")
    elif fails == len(TRIALS):
        print("ALL TRIALS FAILED.")
        print("The downstream write does not fire as modeled.")
        print("Most likely cause: mailbox timing (WRITE_PRIMITIVE.md")
        print("'Timing concern').  The direct overrun is still valid.")
    else:
        print("Mixed results -- see individual trials above.")

    print(f"\nlog: {log}")
    return passes == len(TRIALS)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "--dev", default=DEFAULT_DEV,
        help=f"serial device (default: {DEFAULT_DEV})")
    ap.add_argument(
        "--dry-run", action="store_true",
        help="simulate only, don't talk to the ECU")
    args = ap.parse_args()

    print("c9_write_test: downstream write verification")
    print("Target ECU: 23710-2L904 (1998 Maxima VQ30DE)")
    print(f"Trials: {len(TRIALS)}")
    for i, (target, value, desc) in enumerate(TRIALS, 1):
        persistent = target not in RESET_CLEARS
        print(f"  {i}. ${value:02X} -> ${target:04X}  "
              f"{'persistent' if persistent else 'reset-cleared'}  {desc}")
    print()

    if args.dry_run:
        ok = run_dry()
        raise SystemExit(0 if ok else 1)

    print("-" * 60)
    print("EXPERIMENTAL: tests the unconfirmed downstream write path.")
    print("Writes to at_values only -- no actuator activation.")
    print("Key on, ENGINE OFF.  Key cycle clears all state.")
    print("-" * 60)
    ok = input("Proceed? [y/N] ")
    if ok.strip().lower() != "y":
        sys.exit("not sent")

    success = run_live(args.dev)
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
