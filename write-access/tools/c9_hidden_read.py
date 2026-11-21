#!/usr/bin/env python3
"""c9_hidden_read: read the main CPU's hidden code at $5D40–$623F.

Chains the c9_find_hidden overrun (ROM_ANALYSIS.md §10) with the
consult_reply_direct streamlist dereference (ROM_ANALYSIS.md §11):

  1. PLANT: fire a crafted 20-address C9 overrun that places a chosen
     16-bit address into cs_streamlist ($07A0/$07A1) via the downstream
     OOB write.
  2. VERIFY: read $07A0–$07A3 via one-shot C9 to confirm the plant.
  3. READ (mixed command): send 0A direct-mode + 19 C9 overrun addrs
     in one payload.  The 0A handler loads cs_streamlist from ROM, then
     F0 fires the overrun; during streaming the downstream OOB writes
     overwrite cs_streamlist with our address while consult_reply_direct
     reads from it each frame.  After the plant frames, the direct
     builder dereferences our hidden-region pointer — reading the main
     CPU's own memory with no forwarding.

Phase 3 is the novel part: it avoids the "0A overwrites cs_streamlist"
problem by running the overrun and direct mode *simultaneously*.

Usage:
  python3 write-access/tools/c9_hidden_read.py --dry-run          # simulate only
  python3 write-access/tools/c9_hidden_read.py --sweep --dry-run   # show all targets
  python3 write-access/tools/c9_hidden_read.py                     # live: default addr
  python3 write-access/tools/c9_hidden_read.py --addr 6025         # live: specific addr

The 20-address plant uses the stale c9_sub_value behavior described in
write-access/README.md:
  [0..14]  main_addr × 15
  [15]     $5E0F   (n=$10 after INC, cursor=$0E)
  [16]     $5E0B   (repair $07E3: lo=$0B, bits 0+1 set)
  [17]     $5Xhh   (idx[$0E]=hh, targets cs_payload[hh])
  [18]     $5Xvv   (c9_sub_value=vv, stale write value)
  [19]     $5Xll   (idx[$12]=ll, targets cs_payload[ll])

The mixed 19-address read uses an adapted layout (0A args take 2 argbuf
bytes, leaving room for 19 C9 addrs):
  0A 02 81  +  C9×19  +  F0
Cursor cycle: $0E,$0F,$10,$11,$12,0,1...
Frame 0: idx[$0E]=$61 → stale $60 → $07A1 (streamlist hi)
Frame 2: idx[$10]=$60 → H8 reply → $07A0 (streamlist lo)
After frame 2, cs_streamlist[0]=$60XX; the direct builder dereferences it.

EXPERIMENTAL: this proposed chain failed in the recorded hardware trial.
Controlled writes and hidden reads remain unconfirmed; see
write-access/docs/CONSULT_RAM_MAP.md.
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

CS_PAYLOAD    = 0x0740
CS_STREAMLIST = 0x07A0
HIDDEN_ADDR   = 0x07C3
HIDDEN_IDX    = 0x07D7
HIDDEN_N      = 0x07E1
REPLY_CURSOR  = 0x07E2
FWD_FLAGS     = 0x07E3
C9_SUB_VAL    = 0x07E7
FORWARD_LO    = 0x5D40
FORWARD_HI    = 0x623F
H8_BASE       = 0x0D40
H8_END        = 0x123F


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def simulate_overrun(addr_list):
    """Simulate c9_find_hidden with the given address list.
    Returns ram dict after the overrun completes.
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
    wb(FWD_FLAGS, rb(FWD_FLAGS) & ~0x03)

    for i in range(20):
        if 2 * i >= cs_argc:
            break
        a_val = rw(0x08D2 + 2 * i)
        if not (FORWARD_LO <= a_val < 0x6240):
            if 2 * (i + 1) >= cs_argc:
                break
            continue
        wb(FWD_FLAGS, rb(FWD_FLAGS) | 0x01)
        n = rb(HIDDEN_N)
        addr_idx = (2 * n) & 0xFF
        ww(HIDDEN_ADDR + addr_idx, a_val - 0x5000)
        n_re = rw(HIDDEN_N) & 0xFF
        wb(HIDDEN_IDX + n_re, i & 0xFF)
        wb(HIDDEN_N, (rb(HIDDEN_N) + 1) & 0xFF)
        if 2 * (i + 1) >= cs_argc:
            break
    return ram


def simulate_builder(ram, h8_dump, max_frames=10):
    """Simulate consult_reply_c9 with corrupted state.
    Returns list of (frame, target_addr, value) writes.
    """
    def rb(a): return ram.get(a, 0)
    def wb(a, v): ram[a] = v & 0xFF
    def rw(a): return rb(a) | (rb(a + 1) << 8)

    def h8_byte(h8_addr):
        off = h8_addr - H8_BASE
        return h8_dump[off] if 0 <= off < len(h8_dump) else None

    writes = []
    for frame in range(max_frames):
        flags = rb(FWD_FLAGS)
        if not (flags & 0x01):
            break
        if not (flags & 0x02):
            wb(FWD_FLAGS, rb(FWD_FLAGS) | 0x02)
            wb(REPLY_CURSOR, 0)
            h_addr = rw(HIDDEN_ADDR)
            reply = h8_byte(h_addr)
            if reply is not None:
                wb(C9_SUB_VAL, reply)
            continue

        sub_val = rb(C9_SUB_VAL)
        cursor = rb(REPLY_CURSOR)
        idx_val = rb(HIDDEN_IDX + cursor)
        target = CS_PAYLOAD + idx_val
        writes.append((frame, target, sub_val))

        new_cursor = (cursor + 1) & 0xFF
        n = rb(HIDDEN_N)
        if n > 0 and new_cursor >= n:
            new_cursor = 0
        wb(REPLY_CURSOR, new_cursor)

        h_off = (2 * rb(REPLY_CURSOR)) & 0xFF
        h_addr = rw(HIDDEN_ADDR + h_off)
        reply = h8_byte(h_addr)
        if reply is not None:
            wb(C9_SUB_VAL, reply)

    return writes


def load_h8(path):
    with open(path, "rb") as f:
        data = f.read()
    if len(data) != H8_END - H8_BASE + 1:
        sys.exit(f"H8 dump should be {H8_END - H8_BASE + 1} bytes, got {len(data)}")
    return data


# ---------------------------------------------------------------------------
# 20-address plant payload (for Phase 1: plant + verify)
# ---------------------------------------------------------------------------

def build_plant_payload(target_hi, target_lo, h8_dump):
    """Build a 20-address payload that plants (target_hi << 8 | target_lo)
    into cs_streamlist[0].

    Returns (addr_list, stop_frame) or None.
    """
    addr15 = 0x5E0F
    addr16 = 0x5E0B

    for hi_page in (0x0E, 0x0F, 0x10, 0x11, 0x12, 0x0D):
        addr17 = 0x5000 + (hi_page << 8) + 0x61
        if FORWARD_LO <= addr17 <= FORWARD_HI:
            break
    else:
        return None

    for hi_page in (0x0E, 0x0F, 0x10, 0x11, 0x12, 0x0D):
        addr18 = 0x5000 + (hi_page << 8) + (target_hi & 0xFF)
        if FORWARD_LO <= addr18 <= FORWARD_HI:
            break
    else:
        return None

    for hi_page in (0x0E, 0x0F, 0x10, 0x11, 0x12, 0x0D):
        addr19 = 0x5000 + (hi_page << 8) + 0x60
        if FORWARD_LO <= addr19 <= FORWARD_HI:
            break
    else:
        return None

    # main_addr: lo byte determines idx[0..9]. Avoid $60/$61 to prevent
    # early clobbering of streamlist.  Sweep for one whose H8 chain
    # produces target_lo at $07A0.
    safe_los = [lo for lo in range(0x40, 0x60) if lo not in (0x60, 0x61)]
    safe_los += [lo for lo in range(0x62, 0x80)]

    for lo in safe_los:
        for hi_page in (0x0E, 0x0F, 0x10, 0x11, 0x12, 0x0D):
            main_addr = 0x5000 + (hi_page << 8) + lo
            if not (FORWARD_LO <= main_addr <= FORWARD_HI):
                continue

            payload = [main_addr] * 15 + [addr15, addr16, addr17, addr18, addr19]
            ram = simulate_overrun(payload)
            flags = ram.get(FWD_FLAGS, 0)
            if (flags & 0x03) != 0x03:
                continue

            writes = simulate_builder(dict(ram), h8_dump, 12)

            sl_hi = sl_lo = None
            sl_hi_frame = sl_lo_frame = -1
            for frame, target, value in writes:
                if target == CS_STREAMLIST + 1 and sl_hi is None:
                    sl_hi = value
                    sl_hi_frame = frame
                if target == CS_STREAMLIST and sl_lo is None:
                    sl_lo = value
                    sl_lo_frame = frame

            if sl_hi is None or sl_lo is None:
                continue
            if sl_hi != target_hi or sl_lo != target_lo:
                continue

            stop_frame = max(sl_hi_frame, sl_lo_frame)

            # Check no later clobber before we can stop
            clobbered = False
            for frame, target, value in writes:
                if frame > stop_frame:
                    if target == CS_STREAMLIST + 1 and value != sl_hi:
                        clobbered = True
                    if target == CS_STREAMLIST and value != sl_lo:
                        clobbered = True
            if clobbered:
                continue

            return payload, stop_frame

    return None


def sweep_plant_targets(h8_dump):
    """Find all hidden-region addresses achievable with the 20-address plant."""
    addr15 = 0x5E0F
    addr16 = 0x5E0B

    addr17_choices = [a for hp in range(0x0D, 0x13)
                      for a in [0x5000 + (hp << 8) + 0x61]
                      if FORWARD_LO <= a <= FORWARD_HI]

    addr19_choices = [a for hp in range(0x0D, 0x13)
                      for a in [0x5000 + (hp << 8) + 0x60]
                      if FORWARD_LO <= a <= FORWARD_HI]

    safe_los = [lo for lo in range(0x40, 0x60) if lo not in (0x60, 0x61)]
    safe_los += [lo for lo in range(0x62, 0x80)]

    results = {}
    for target_hi in range(0x5D, 0x63):
        addr18_choices = [a for hp in range(0x0D, 0x13)
                          for a in [0x5000 + (hp << 8) + target_hi]
                          if FORWARD_LO <= a <= FORWARD_HI]

        for addr18 in addr18_choices:
            for addr17 in addr17_choices:
                for addr19 in addr19_choices:
                    for lo in safe_los:
                        for hp in (0x0E, 0x0F, 0x10, 0x11, 0x12, 0x0D):
                            main = 0x5000 + (hp << 8) + lo
                            if not (FORWARD_LO <= main <= FORWARD_HI):
                                continue
                            payload = [main] * 15 + [addr15, addr16, addr17, addr18, addr19]
                            ram = simulate_overrun(payload)
                            flags = ram.get(FWD_FLAGS, 0)
                            if (flags & 0x03) != 0x03:
                                continue
                            writes = simulate_builder(dict(ram), h8_dump, 12)

                            sl_hi = sl_lo = None
                            sf_hi = sf_lo = -1
                            for f, t, v in writes:
                                if t == CS_STREAMLIST + 1 and sl_hi is None:
                                    sl_hi = v; sf_hi = f
                                if t == CS_STREAMLIST and sl_lo is None:
                                    sl_lo = v; sf_lo = f

                            if sl_hi is None or sl_lo is None:
                                continue
                            addr = (sl_hi << 8) | sl_lo
                            if not (0x5D40 <= addr <= 0x623F):
                                continue
                            stop = max(sf_hi, sf_lo)

                            ok = True
                            for f, t, v in writes:
                                if f > stop:
                                    if t == CS_STREAMLIST + 1 and v != sl_hi:
                                        ok = False
                                    if t == CS_STREAMLIST and v != sl_lo:
                                        ok = False
                            if not ok:
                                continue

                            if addr not in results:
                                results[addr] = (main, addr17, addr18, addr19,
                                                 sl_hi, sl_lo, sf_hi, sf_lo, stop)
                            break  # found one main for this combo, move on
                        else:
                            continue
                        break  # found one, skip remaining hp choices
    return results


# ---------------------------------------------------------------------------
# 19-address mixed payload (for Phase 3: simultaneous read)
# ---------------------------------------------------------------------------

def build_mixed_payload():
    """Build the 0A+C9 mixed command payload.

    Returns (0A_bytes, c9_addr_list):
      0A_bytes = bytes([0x0A, 0x02, 0x81])  (direct mode, fb=2 val=$81)
      c9_addr_list = 19 C9 addresses

    The 0A args take 2 bytes of cs_argbuf (pair 0, skipped by c9_find_hidden).
    With 19 C9 addrs: total argc = 2 + 38 = 40 (at the limit).

    Layout (14 main + 5 control): the 0A pair shifts i by 1, so we use
    14 main addresses (not 15) so that the first control addr lands at n=15
    where addr_store hits $07E1.  The 5th control is a dummy (main_addr).

      idx[$0E]=$61 → frame 0 stale ($60) → $07A1
      idx[$10]=$60 → frame 2 H8 reply → $07A0
      Streamlist = $60XX after frame 2
    """
    addr15 = 0x5E0F
    addr16 = 0x5E0B
    addr17 = 0x5E61  # idx[$0E] = $61
    addr18 = 0x5E60  # c9_sub_value = $60, idx[$10] = $60
    main_addr = 0x5E50  # safe lo=$50, avoids $60/$61

    c9_addrs = [main_addr] * 14 + [addr15, addr16, addr17, addr18, main_addr]
    return bytes([0x0A, 0x02, 0x81]), c9_addrs


# ---------------------------------------------------------------------------
# Live execution
# ---------------------------------------------------------------------------

def read_c9(c, addrs):
    """Read addresses via C9 one-shot (max 8 per call)."""
    result = bytearray()
    for i in range(0, len(addrs), 8):
        chunk = addrs[i:i + 8]
        result += c.read_memory(chunk)
    return bytes(result)


def run_plant(c, payload, stop_frame, target_addr):
    """Phase 1: fire the 20-address overrun to plant cs_streamlist."""
    n_addrs = len(payload)
    n_frames = stop_frame + 1  # frame numbers are zero-based; no extra mutations

    print(f"\n--- Phase 1: PLANT (target ${target_addr:04X}) ---")
    print(f"  Sending {n_addrs} C9 addresses + F0...")

    cmd = b"".join(bytes([0xC9, a >> 8, a & 0xFF]) for a in payload)
    frames = mutation_stream(c, cmd, frames=n_frames, expected_len=n_addrs)
    print(f"  Streamed {len(frames)} frames, stopped.")
    return frames


def run_verify(c, target_addr):
    """Phase 2: read cs_streamlist via C9 to confirm the plant."""
    print(f"\n--- Phase 2: VERIFY ---")
    sl = read_c9(c, [CS_STREAMLIST, CS_STREAMLIST + 1,
                      CS_STREAMLIST + 2, CS_STREAMLIST + 3])
    word0 = sl[0] | (sl[1] << 8)
    word1 = sl[2] | (sl[3] << 8)
    print(f"  cs_streamlist[0] = ${word0:04X}  (${sl[1]:02X} ${sl[0]:02X})")
    print(f"  cs_streamlist[1] = ${word1:04X}  (${sl[3]:02X} ${sl[2]:02X})")

    if word0 == target_addr:
        print(f"  PLANT CONFIRMED: streamlist[0] = ${target_addr:04X}")
    else:
        print(f"  PLANT MISMATCH: expected ${target_addr:04X}, got ${word0:04X}")
        raise ConsultError("plant readback mismatch; no follow-up mutation permitted")

    return word0, word1


def run_mixed(c, n_frames=12):
    """Phase 3: mixed 0A+C9 command — overrun + direct mode simultaneously."""
    print(f"\n--- Phase 3: MIXED READ (0A direct + C9 overrun) ---")

    oa_bytes, c9_addrs = build_mixed_payload()
    n_c9 = len(c9_addrs)

    # Build the full command payload: 0A 02 81 C9 xx xx ... (×19)
    cmd = bytearray(oa_bytes)
    for a in c9_addrs:
        cmd += bytes([0xC9, a >> 8, a & 0xFF])
    cmd = bytes(cmd)

    print(f"  Sending 0A 02 81 + {n_c9}×C9 + F0...")
    print(f"  (0A activates direct mode; C9 overrun plants streamlist during streaming)")

    frames = mutation_stream(c, cmd, frames=n_frames)

    print(f"  Streamed {len(frames)} frames.")
    print(f"\n  Raw frames:")
    for i, f in enumerate(frames):
        hex_str = " ".join(f"{b:02X}" for b in f)
        print(f"    [{i:2d}] len={len(f):2d}  {hex_str}")

    return frames


def run_direct_baseline(c, n_frames=4):
    """Baseline: run 0A direct mode alone to see its frame format."""
    print(f"\n--- Baseline: 0A direct mode alone ---")
    print(f"  Sending 0A 02 81 + F0...")

    cmd = bytes([0x0A, 0x02, 0x81])
    frames = mutation_stream(c, cmd, frames=n_frames)

    print(f"  Streamed {len(frames)} frames.")
    for i, f in enumerate(frames):
        hex_str = " ".join(f"{b:02X}" for b in f)
        print(f"    [{i:2d}] len={len(f):2d}  {hex_str}")

    return frames


# ---------------------------------------------------------------------------
# Dry run
# ---------------------------------------------------------------------------

def dry_run_plant(target_addr, h8_dump):
    """Simulate the plant and show what would happen."""
    target_hi = (target_addr >> 8) & 0xFF
    target_lo = target_addr & 0xFF

    result = build_plant_payload(target_hi, target_lo, h8_dump)
    if result is None:
        print(f"  No payload found for ${target_addr:04X} with this H8 dump.")
        return False

    payload, stop_frame = result

    print(f"  Target:     ${target_addr:04X} (hi=${target_hi:02X} lo=${target_lo:02X})")
    print(f"  Main addr:  ${payload[0]:04X}")
    print(f"  Payload:    15×${payload[0]:04X} + ${payload[15]:04X} ${payload[16]:04X} "
          f"${payload[17]:04X} ${payload[18]:04X} ${payload[19]:04X}")
    print(f"  Stop after: frame {stop_frame}")

    ram = simulate_overrun(payload)
    writes = simulate_builder(dict(ram), h8_dump, stop_frame + 4)

    print(f"\n  Reply builder writes:")
    for frame, target, value in writes:
        lbl = ""
        if target == CS_STREAMLIST:
            lbl = " ← streamlist[0] lo"
        elif target == CS_STREAMLIST + 1:
            lbl = " ← streamlist[0] hi"
        print(f"    frame {frame:2d}: → ${target:04X} = ${value:02X}{lbl}")

    return True


def dry_run_sweep(h8_dump):
    """Show all achievable hidden-region addresses."""
    results = sweep_plant_targets(h8_dump)
    if not results:
        print("  No hidden-region addresses achievable with this H8 dump.")
        return

    print(f"  Achievable hidden-region addresses: {len(results)}")
    print()
    pages = {}
    for addr in sorted(results):
        page = addr >> 8
        pages.setdefault(page, []).append(addr)
        main, a17, a18, a19, hi, lo, hf, lf, sf = results[addr]
        print(f"    ${addr:04X}  main=${main:04X}  "
              f"hi=${hi:02X}@f{hf} lo=${lo:02X}@f{lf}  stop@f{sf}")

    print(f"\n  Coverage: {len(results)} / {FORWARD_HI - FORWARD_LO + 1} "
          f"({100 * len(results) / (FORWARD_HI - FORWARD_LO + 1):.1f}%)")
    for page in sorted(pages):
        print(f"    ${page:02X}xx: {len(pages[page])} addrs")


def dry_run_mixed():
    """Show the mixed command layout."""
    print(f"\n--- Mixed command (0A + C9 overrun) ---")
    oa_bytes, c9_addrs = build_mixed_payload()
    print(f"  0A args:    {oa_bytes.hex(' ')}")
    print(f"  C9 addrs:   {len(c9_addrs)} (14×${c9_addrs[0]:04X} + "
          + " ".join(f"${a:04X}" for a in c9_addrs[14:]) + ")")
    print(f"  Total args: 2 + {len(c9_addrs)*2} = {2 + len(c9_addrs)*2} bytes (limit 40)")

    # Simulate the overrun as the ECU would see it (0A args at argbuf[0..1])
    # The 0A arg bytes go into cs_argbuf as received: [fb=02, val=81].
    # The M37732 reads 16-bit words little-endian, so pair 0 = $8102.
    # But the simulation's ww/rw is self-consistent, so we pass the
    # protocol-order value $0281 and it stays consistent.
    all_pairs = [0x0281] + c9_addrs
    ram = simulate_overrun_mixed(all_pairs)
    flags = ram.get(FWD_FLAGS, 0)
    print(f"  $07E3 = ${flags:02X}  bit0={'SET' if flags & 1 else 'CLR'}  "
          f"bit1={'SET' if flags & 2 else 'CLR'}")

    n_final = ram.get(HIDDEN_N, 0)
    cursor = ram.get(REPLY_CURSOR, 0)
    print(f"  n=${n_final:02X}  cursor=${cursor:02X}")

    idx_0e = ram.get(HIDDEN_IDX + 0x0E, 0)
    idx_10 = ram.get(HIDDEN_IDX + 0x10, 0)
    sub = ram.get(C9_SUB_VAL, 0)
    print(f"  idx[$0E]=${idx_0e:02X} → cs_payload[${idx_0e:02X}] = ${CS_PAYLOAD + idx_0e:04X}")
    print(f"  idx[$10]=${idx_10:02X} → cs_payload[${idx_10:02X}] = ${CS_PAYLOAD + idx_10:04X}")
    print(f"  c9_sub_value=${sub:02X} (stale byte for frame 0)")
    print()
    print(f"  Expected: frame 0 writes ${sub:02X} to ${CS_PAYLOAD + idx_0e:04X}")
    print(f"            frame 2 writes H8 reply to ${CS_PAYLOAD + idx_10:04X}")
    if idx_0e == 0x61 and idx_10 == 0x60:
        print(f"            → streamlist[0] = ${sub:02X}XX (page ${sub:02X}, lo from H8)")
    elif idx_0e == 0x60 and idx_10 == 0x61:
        print(f"            → streamlist[0] = XX{sub:02X} (hi from H8, lo ${sub:02X})")


def simulate_overrun_mixed(all_pairs):
    """Simulate c9_find_hidden with cs_argbuf containing 0A args + C9 addrs."""
    ram = {}
    def rb(a): return ram.get(a, 0)
    def wb(a, v): ram[a] = v & 0xFF
    def rw(a): return rb(a) | (rb(a + 1) << 8)
    def ww(a, v): wb(a, v & 0xFF); wb(a + 1, (v >> 8) & 0xFF)

    cs_argc = len(all_pairs) * 2
    for i, a in enumerate(all_pairs):
        ww(0x08D2 + 2 * i, a)
    wb(HIDDEN_N, 0)
    wb(FWD_FLAGS, rb(FWD_FLAGS) & ~0x03)

    for i in range(20):
        if 2 * i >= cs_argc:
            break
        a_val = rw(0x08D2 + 2 * i)
        if not (FORWARD_LO <= a_val < 0x6240):
            if 2 * (i + 1) >= cs_argc:
                break
            continue
        wb(FWD_FLAGS, rb(FWD_FLAGS) | 0x01)
        n = rb(HIDDEN_N)
        addr_idx = (2 * n) & 0xFF
        ww(HIDDEN_ADDR + addr_idx, a_val - 0x5000)
        n_re = rw(HIDDEN_N) & 0xFF
        wb(HIDDEN_IDX + n_re, i & 0xFF)
        wb(HIDDEN_N, (rb(HIDDEN_N) + 1) & 0xFF)
        if 2 * (i + 1) >= cs_argc:
            break
    return ram


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dev", default=DEFAULT_DEV,
                    help=f"serial device (default: {DEFAULT_DEV})")
    ap.add_argument("--addr", type=lambda x: int(x, 16), default=None,
                    help="target hidden-region address in hex (default: auto from sweep)")
    ap.add_argument("--h8", default=os.path.join(ROOT, "write-access", "h8", "h8_clean.bin"),
                    help="H8 dump for simulation (default: write-access/h8/h8_clean.bin)")
    ap.add_argument("--sweep", action="store_true",
                    help="show all achievable target addresses")
    ap.add_argument("--mixed-only", action="store_true",
                    help="skip the plant+verify phases, run mixed command only")
    ap.add_argument("--frames", type=int, default=12,
                    help="frames to stream in mixed phase (default: 12)")
    ap.add_argument("--dry-run", action="store_true",
                    help="simulate only, don't talk to the ECU")
    args = ap.parse_args()
    if not 1 <= args.frames <= 1000:
        ap.error("--frames must be in 1..1000")

    print("c9_hidden_read: read main CPU hidden code via overrun + streamlist chain")
    print("Target ECU: 23710-2L904 (1998 Maxima VQ30DE)")
    print()

    h8_dump = None
    if os.path.exists(args.h8):
        h8_dump = load_h8(args.h8)
        print(f"H8 dump: {args.h8} ({len(h8_dump)} bytes)")
    else:
        print(f"H8 dump not found: {args.h8}")
        print("  (needed for plant simulation; mixed behavior is unconfirmed)")

    # --- Sweep ---
    if args.sweep:
        if h8_dump is None:
            sys.exit("--sweep requires an H8 dump (--h8)")
        print()
        dry_run_sweep(h8_dump)
        print()
        dry_run_mixed()
        return

    # --- Pick target ---
    target_addr = args.addr
    sweep_results = None
    if target_addr is not None:
        if not (FORWARD_LO <= target_addr <= FORWARD_HI):
            sys.exit(f"target ${target_addr:04X} outside hidden region "
                     f"${FORWARD_LO:04X}–${FORWARD_HI:04X}")
    elif h8_dump is not None:
        sweep_results = sweep_plant_targets(h8_dump)
        if sweep_results:
            # Pick a target the plant builder can actually produce a payload for
            for candidate in sorted(sweep_results.keys()):
                hi = (candidate >> 8) & 0xFF
                lo = candidate & 0xFF
                if build_plant_payload(hi, lo, h8_dump) is not None:
                    target_addr = candidate
                    break
            if target_addr is not None:
                print(f"Auto-selected target: ${target_addr:04X} "
                      f"({len(sweep_results)} achievable by sweep)")
            else:
                print(f"Sweep found {len(sweep_results)} targets but plant "
                      f"builder can't produce payloads for them; using mixed only.")
        else:
            print("No plant targets found; will run mixed command only.")
    else:
        print("No H8 dump and no --addr; will run mixed command only.")

    # --- Dry run ---
    if args.dry_run:
        if target_addr is not None and h8_dump is not None:
            print(f"\n--- Plant simulation for ${target_addr:04X} ---")
            dry_run_plant(target_addr, h8_dump)
        dry_run_mixed()
        return

    # --- Live ---
    print()
    print("-" * 60)
    print("EXPERIMENTAL: controlled writes and hidden reads remain unconfirmed.")
    print("Live handler state may be corrupted; reset behavior requires verification.")
    print("Run with key on, ENGINE OFF.")
    print("-" * 60)
    ok = input("Proceed? [y/N] ")
    if ok.strip().lower() != "y":
        sys.exit("not sent")
    print()

    os.makedirs(LOG_DIR, exist_ok=True)
    log = os.path.join(LOG_DIR, f"{datetime.date.today()}_hidden-read.log")
    t = Transport(args.dev, log)
    t.note("c9_hidden_read start")

    try:
        c = Consult(t)
        c.ecu_ids = ENGINE_IDS

        r = c.init()
        if r is None:
            sys.exit("init failed (ignition on?)")
        attempt, secs, junk, ecu = r
        require_research_ecu(c)
        print(f"\ninit ok: id {ecu:02X}, attempt {attempt}, {secs * 1000:.0f} ms")

        # Baseline streamlist
        sl_before = read_c9(c, [CS_STREAMLIST, CS_STREAMLIST + 1,
                                 CS_STREAMLIST + 2, CS_STREAMLIST + 3])
        print(f"  streamlist before: {sl_before.hex(' ')}")

        if args.mixed_only:
            run_mixed(c, args.frames)
            print("Mixed frames are unverified observations, not hidden-code read proof.")
            return

        if not args.mixed_only and target_addr is not None and h8_dump is not None:
            # Phase 1: Plant
            target_hi = (target_addr >> 8) & 0xFF
            target_lo = target_addr & 0xFF
            result = build_plant_payload(target_hi, target_lo, h8_dump)
            if result is None:
                raise ConsultError(f"no plant payload for ${target_addr:04X}; nothing sent")
            else:
                payload, stop_frame = result
                run_plant(c, payload, stop_frame, target_addr)

                # Phase 2: Verify
                word0, word1 = run_verify(c, target_addr)

        # A second mutation requires its own verified starting state. Re-init
        # does not establish that state or preserve a planted streamlist.
        print("Plant trial ended. No automatic direct-mode or mixed follow-up.")
        return

    except (OSError, ValueError) as e:
        print(f"\nerror: {e}")
        raise SystemExit(1) from e
    finally:
        t.close()
        print(f"\nlog: {log}")


if __name__ == "__main__":
    main()
