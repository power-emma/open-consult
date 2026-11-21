#!/usr/bin/env python3
"""Definitive downstream write test: target cs_payload[0] ($0740).

If the builder at $9B5E writes to cs_payload[idx[cursor]], and we set
idx[$0E] = $00, it writes to cs_payload[0] = position 0 of the reply frame.

Phase 1 fills position 0 with the H8 response for $5E00 (was $03 last run).
Phase 2 (builder) overwrites it with the clobbered c9_sub_value.

If frame[0] differs from a normal run's frame[0], the downstream write IS firing.
If frame[0] is the same, it isn't.

We also run a CONTROL first (normal 10-addr C9 read of $5E00×10) to establish
what the H8 responds with under identical conditions.
"""
import os, sys, time, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from consult.protocol import Consult, ConsultError, ENGINE_IDS
from consult.transport import DEFAULT_DEV, Transport
from consult.experimental import mutation_stream, require_research_ecu
from consult.write import HIDDEN_N, REPLY_CURSOR, FWD_FLAGS, C9_SUB_VAL

LOG_DIR = os.path.join(ROOT, "logs")

PROBE_ADDR = 0x07BD

def build_payload():
    """20-address overrun payload targeting cs_payload[0].

    idx[$0E] = $00 → builder writes to $0740 + $00 = $0740 = cs_payload[0].
    Position 17 = $5E00 (low byte $00 → idx[$0E] = $00).
    Position 18 = $5EFF (value doesn't matter — gets clobbered).
    Position 19 = PROBE_ADDR (non-forwarded, direct bank-0 read).
    """
    main     = 0x5E00
    repair_a = 0x5E0A
    repair_b = 0x5E0B
    tgt_addr = 0x5E00  # low byte $00 = target idx for cs_payload[0]
    val_addr = 0x5EFF  # arbitrary (value will be clobbered by mailbox)
    payload = [main] * 15 + [repair_a, repair_b, tgt_addr, val_addr, PROBE_ADDR]
    return payload


def main():
    print("c9_write_framehit: definitive downstream write test")
    print(f"Target: cs_payload[0] ($0740) — position 0 of the reply frame")
    print(f"idx[$0E] = $00 → builder writes clobber to frame position 0")
    print(f"Probe (position 19): ${PROBE_ADDR:04X}")
    print()

    payload = build_payload()
    print(f"Payload:")
    for i, a in enumerate(payload):
        tag = ""
        if i == 15: tag = " (repair_a)"
        elif i == 16: tag = " (repair_b)"
        elif i == 17: tag = " (target idx: $00 → cs_payload[0])"
        elif i == 18: tag = " (value carrier — will be clobbered)"
        elif i == 19: tag = f" (probe: ${PROBE_ADDR:04X}, NOT forwarded)"
        elif i == 0: tag = " (×15)"
        elif 1 <= i <= 14: continue
        print(f"  [{i:2d}] ${a:04X}{tag}")
    print()

    print("-" * 60)
    print("PHASE 1 fills frame[0] with H8 response for $5E00.")
    print("PHASE 2 (builder) overwrites frame[0] with clobber.")
    print("If frame[0] DIFFERS between frame 0 and frame 1,")
    print("  the downstream write is confirmed.")
    print("Run with key on, ENGINE OFF.")
    print("-" * 60)
    if input("Proceed? [y/N] ").strip().lower() != "y":
        return

    os.makedirs(LOG_DIR, exist_ok=True)
    log = os.path.join(LOG_DIR, f"{datetime.date.today()}_c9-framehit.log")
    t = Transport(DEFAULT_DEV, log)
    t.note("c9_write_framehit start")

    try:
        c = Consult(t)
        r = c.init()
        if r is None:
            sys.exit("init failed")
        attempt, secs, _, ecu = r
        require_research_ecu(c)
        print(f"\ninit ok: id {ecu:02X}, attempt {attempt}, {secs*1000:.0f} ms")

        # --- Control: normal 8-addr C9 read to see H8 response for $5E00 ---
        print(f"\nControl: normal C9 read of $5E00 ×8...")
        control = c.read_memory([0x5E00] * 8)
        print(f"  H8 responses for $5E00 ×8: {' '.join(f'${b:02X}' for b in control)}")
        # Also read probe baseline
        probe_base = c.read_memory([PROBE_ADDR])
        print(f"  Probe ${PROBE_ADDR:04X} = ${probe_base[0]:02X}")

        # --- Overrun: 20 addresses + F0, stream 3 frames ---
        cmd = b"".join(bytes([0xC9, a >> 8, a & 0xFF]) for a in payload)
        print(f"\nSending 20-address overrun + F0 (3 frames)...")
        frames = mutation_stream(c, cmd, frames=3, expected_len=len(payload))
        print(f"  got {len(frames)} frame(s)")

        for fi, frame in enumerate(frames):
            print(f"\n  Frame {fi} ({len(frame)} bytes):")
            for i, b in enumerate(frame):
                tag = ""
                if i == 0:
                    # This is the key byte — did the builder overwrite it?
                    expected = control[0] if len(control) > 0 else None
                    if expected is not None and b != expected:
                        tag = f"  *** DIFFERS from control ${expected:02X} — WRITE CONFIRMED ***"
                    else:
                        tag = f"  (control was ${expected:02X})" if expected is not None else ""
                elif i == 19:
                    tag = f"  <- probe ${PROBE_ADDR:04X}"
                elif i == 18:
                    tag = f"  <- pos 18 (last forwarded → determines clobber)"
                print(f"    [{i:2d}] ${b:02X}{tag}")

        # Compare frame[0] across frames
        if len(frames) >= 2:
            print(f"\n  Cross-frame comparison (position 0):")
            for fi, frame in enumerate(frames):
                print(f"    frame {fi}: position 0 = ${frame[0]:02X}")

        # --- Post-stop readback ---
        print(f"\nPost-stop readback...")
        r2 = c.init()
        if r2:
            diag = c.read_memory([0x07E1, 0x07E2, 0x07E3, 0x07E5, 0x07E7, PROBE_ADDR])
            names = ["n", "cursor", "flags", "idx[$0E]", "sub_val", f"${PROBE_ADDR:04X}"]
            for name, val in zip(names, diag):
                print(f"  {name:12s} = ${val:02X}")
        else:
            print("  re-init failed")

        # Verdict
        print(f"\n{'='*60}")
        if frames:
            f0_pos0 = frames[0][0]
            ctrl_pos0 = control[0] if control else None
            if ctrl_pos0 is not None and f0_pos0 != ctrl_pos0:
                print(f"DOWNSTREAM WRITE CONFIRMED.")
                print(f"  Control frame[0] = ${ctrl_pos0:02X}")
                print(f"  Overrun frame[0] = ${f0_pos0:02X}")
                print(f"  Builder overwrote cs_payload[0] with clobber value.")
                print(f"  The mailbox clobber replaced our value with the H8 response.")
                print(f"  FIX: choose position 18 so H8 response = desired value.")
            else:
                print(f"NO DOWNSTREAM WRITE DETECTED.")
                print(f"  frame[0] = ${f0_pos0:02X}, control = ${ctrl_pos0:02X}")
                if f0_pos0 == ctrl_pos0:
                    print(f"  Could be: (a) write fires but clobber == H8 response,")
                    print(f"            (b) write doesn't fire at all.")
                    print(f"  Check if frame[0] differs between frame 0 and frames 1-2.")
        print(f"{'='*60}")

    except (OSError, ValueError, ConsultError) as e:
        print(f"\nerror: {e}")
    finally:
        t.close()
        print(f"\nlog: {log}")


if __name__ == "__main__":
    main()
