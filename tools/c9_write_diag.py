#!/usr/bin/env python3
"""Diagnostic: does the downstream builder fire?  Target $07BD (baseline $03,
persists through stop) and dump full frame bytes to see what c9_sub_value
the builder actually used.

If the builder writes the H8 response (not our value) to $07BD, we'll see
$07BD change from $03 to something other than $FF.  If it stays $03, the
builder isn't firing the OOB write at all.
"""
import os, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from consult.protocol import Consult, ConsultError, ENGINE_IDS
from consult.transport import DEFAULT_DEV, Transport
from consult.experimental import mutation_stream, require_research_ecu
from consult.write import compute_payload, simulate_overrun, C9_SUB_VAL, HIDDEN_N, REPLY_CURSOR, FWD_FLAGS

TARGET = 0x07BD
VALUE  = 0xFF

LOG_DIR = os.path.join(ROOT, "logs")

DIAG_ADDRS = [
    0x07BD,             # target (at_active[6], baseline $03, NOT reset-cleared)
    0x07E1,             # c9_hidden_n
    0x07E2,             # reply_cursor
    0x07E3,             # fwd_flags
    0x07E5,             # idx[$0E]
    0x07E7,             # c9_sub_value
    0x07E8, 0x07E9,     # adjacent (overrun spill)
]

def read_diag(c):
    """Read diagnostic addresses via C9 (all below $5D40, no forwarding)."""
    result = {}
    for i in range(0, len(DIAG_ADDRS), 8):
        chunk = DIAG_ADDRS[i:i+8]
        data = c.read_memory(chunk)
        for a, v in zip(chunk, data):
            result[a] = v
    return result

def main():
    payload = compute_payload(TARGET, VALUE)

    print(f"c9_write_diag: does the downstream OOB write fire?")
    print(f"Target: ${TARGET:04X} (at_active[6], baseline should be $03)")
    print(f"Value:  ${VALUE:02X}")
    print(f"Probe:  position 19 replaced with ${TARGET:04X} for in-stream read")
    print()

    # Dry-run simulation
    ram, stores = simulate_overrun(payload)
    print(f"Simulation post-overrun:")
    print(f"  $07E1 (n)       = ${ram.get(HIDDEN_N, 0):02X}")
    print(f"  $07E2 (cursor)  = ${ram.get(REPLY_CURSOR, 0):02X}")
    print(f"  $07E3 (flags)   = ${ram.get(FWD_FLAGS, 0):02X}")
    print(f"  $07E5 (idx[14]) = ${ram.get(0x07E5, 0):02X}")
    print(f"  $07E7 (sub_val) = ${ram.get(C9_SUB_VAL, 0):02X}")
    print()

    # Replace position 19 with target for in-stream probe
    payload[19] = TARGET

    print("-" * 60)
    print("Run with key on, ENGINE OFF.")
    print("-" * 60)
    if input("Proceed? [y/N] ").strip().lower() != "y":
        return

    os.makedirs(LOG_DIR, exist_ok=True)
    log = os.path.join(LOG_DIR, f"{__import__('datetime').date.today()}_c9-write-diag.log")
    t = Transport(DEFAULT_DEV, log)
    t.note("c9_write_diag start")

    try:
        c = Consult(t)
        r = c.init()
        if r is None:
            sys.exit("init failed")
        attempt, secs, _, ecu = r
        require_research_ecu(c)
        print(f"\ninit ok: id {ecu:02X}, attempt {attempt}, {secs*1000:.0f} ms")

        # Baseline
        base = read_diag(c)
        print(f"\nBaseline:")
        for a in DIAG_ADDRS:
            print(f"  ${a:04X} = ${base[a]:02X}")

        target_before = base[TARGET]
        print(f"\n  target ${TARGET:04X} = ${target_before:02X} (expect $03)")

        # Fire overrun + stream 1 frame
        cmd = b"".join(bytes([0xC9, a >> 8, a & 0xFF]) for a in payload)
        print(f"\nSending 20 C9 addresses + F0 (1 frame)...")
        frames = mutation_stream(c, cmd, frames=1, expected_len=len(payload))
        print(f"  got {len(frames)} frame(s)")

        # Dump full frame
        if frames:
            f0 = frames[0]
            print(f"\n  Frame 0 ({len(f0)} bytes):")
            # Positions 0-18 are forwarded replies, position 19 is direct read
            for i, b in enumerate(f0):
                tag = ""
                if i == 19:
                    tag = f"  <- probe ${TARGET:04X} (direct bank-0 read)"
                elif i == 18:
                    tag = f"  <- pos 18 (value carrier: ${payload[18]:04X})"
                elif i == 15:
                    tag = f"  <- pos 15 (repair_a: ${payload[15]:04X})"
                elif i == 16:
                    tag = f"  <- pos 16 (repair_b: ${payload[16]:04X})"
                elif i == 17:
                    tag = f"  <- pos 17 (target idx: ${payload[17]:04X})"
                print(f"    [{i:2d}] ${b:02X}{tag}")

        # Post-stop readback
        print(f"\nPost-stop readback:")
        # Re-init to read (stop already happened in mutation_stream)
        r2 = c.init()
        if r2 is None:
            print("  re-init failed")
        else:
            after = read_diag(c)
            for a in DIAG_ADDRS:
                changed = " **CHANGED**" if after[a] != base[a] else ""
                print(f"  ${a:04X} = ${after[a]:02X} (was ${base[a]:02X}){changed}")

            target_after = after[TARGET]
            print()
            if target_after == VALUE:
                print(f"  WRITE CONFIRMED: ${TARGET:04X} changed from ${target_before:02X} to ${VALUE:02X}")
            elif target_after != target_before:
                print(f"  BUILDER FIRED but wrong value: ${TARGET:04X} = ${target_after:02X}")
                print(f"    Expected ${VALUE:02X}, got ${target_after:02X}")
                print(f"    -> mailbox_receive likely clobbered c9_sub_value")
            else:
                print(f"  NO CHANGE: ${TARGET:04X} still ${target_after:02X}")
                print(f"    Builder may not be firing the OOB write")

    except (OSError, ValueError, ConsultError) as e:
        print(f"\nerror: {e}")
    finally:
        t.close()
        print(f"\nlog: {log}")

if __name__ == "__main__":
    main()
