#!/usr/bin/env python3
"""c9_h8_dump: read the second CPU (H8/3437) via Consult C9 forwarding.

Addresses $5D40–$623F are forwarded by the engine ECU to the second CPU,
mapping to the H8's $0D40–$123F (1280 bytes). This script reads them in
small batches (≤8 per request, within c9_hidden's 10-entry limit) and
builds a hex dump of the H8's visible address space.

H8 values arrive asynchronously: the ECU fills one payload slot per reply
frame, cycling through the queued addresses ($9B3F), so a single frame is
just one phase of that loop. Each batch streams a budget of frames and
majority-decodes per slot, flagging (??) any slot that never settles.

Batch-size caveat: with batch=8, positions 6-7 of every batch are
contaminated by the c9_hidden reply mechanism ($0E/$1E artifacts). Use
--batch 6 for a clean dump, or --patch to re-read only the contaminated
positions from a prior batch=8 dump.

Usage: python3 write-access/tools/c9_h8_dump.py [--dev /dev/ttyUSB0] [--range 5D40-623F]
                                   [--batch 6] [--frames 4] [--out dump.bin]
       python3 write-access/tools/c9_h8_dump.py --patch prior.bin --out clean.bin
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

LOG_DIR = os.path.join(ROOT, "logs")

FORWARD_LO = 0x5D40
FORWARD_HI = 0x623F
H8_OFFSET  = 0x5000
BATCH_SIZE  = 6
OLD_BATCH   = 8
CONTAMINATED_POS = (6, 7)


def contaminated_offsets(total, old_batch=OLD_BATCH, positions=CONTAMINATED_POS):
    """Return sorted list of byte offsets that were contaminated in a prior dump."""
    offsets = []
    for i in range(0, total, old_batch):
        for p in positions:
            if i + p < total:
                offsets.append(i + p)
    return sorted(offsets)


def read_forwarded(c, addrs, frames=0):
    """Stream one forwarded C9 block and majority-decode one byte per address.

    The ECU queues every C9 address in the forwarded range and then fills one
    payload slot per reply frame from the second CPU, cycling through the queue
    (consult_reply_c9 tail, $9B3F). So a block of B addresses needs ~B+1 frames
    before every slot holds a real byte; taking a single frame (even "the last"
    one) just captures one arbitrary phase of that loop. We read a budget of
    frames and, per slot, keep the value only if the later frames agree, flagging
    any slot that never settles.

    Returns (values, ok): ok[i] is False when slot i did not converge.
    """
    n = len(addrs)
    budget = frames if frames else 2 * n + 6
    payload = b"".join(bytes([0xC9, a >> 8, a & 0xFF]) for a in addrs)
    got = []
    try:
        c.command(payload)
        for _ in range(budget):
            try:
                got.append(list(c.read_frame(expected_len=n)))
            except TimeoutError:
                break
    finally:
        c.stop(timeout=0.5)
        c.t.drain(quiet=0.05)
    # Use the later half of the frames (the pipeline has filled by then) and keep
    # a slot only when those frames agree.
    late = got[len(got) // 2:]
    values, ok = bytearray(n), [False] * n
    for i in range(n):
        col = [f[i] for f in late if i < len(f)]
        values[i] = col[-1] if col else 0
        ok[i] = len(col) >= 2 and len(set(col)) == 1
    return values, ok


def hex_dump(data, base, width=16):
    lines = []
    for off in range(0, len(data), width):
        row = data[off:off + width]
        hex_part = " ".join(f"{b:02X}" for b in row)
        ascii_part = "".join(chr(b) if 0x20 <= b < 0x7F else "." for b in row)
        lines.append(f"  ${base + off:04X}: {hex_part:<{width * 3 - 1}s}  {ascii_part}")
    return "\n".join(lines)


def run_patch(args, lo, hi, h8_lo, h8_hi, all_addrs, batch_sz):
    """Re-read only the contaminated positions from a prior batch-8 dump."""
    with open(args.patch, "rb") as f:
        prior = bytearray(f.read())
    if len(prior) != len(all_addrs):
        sys.exit(f"prior dump is {len(prior)} bytes, expected {len(all_addrs)}")

    bad_offsets = contaminated_offsets(len(prior))
    bad_addrs = [all_addrs[o] for o in bad_offsets]
    n_batches = (len(bad_addrs) + batch_sz - 1) // batch_sz

    print(f"c9_h8_dump --patch: re-reading {len(bad_addrs)} contaminated positions")
    print(f"Prior dump: {args.patch} ({len(prior)} bytes)")
    fshow = args.frames if args.frames else f"auto(~{2 * batch_sz + 6})"
    print(f"Batches:    {n_batches} × ≤{batch_sz}, {fshow} frames each")
    print()

    if args.dry_run:
        print("(dry run — would re-read the above positions)")
        for o in bad_offsets[:16]:
            a = all_addrs[o]
            print(f"  offset {o:4d}  ECU ${a:04X}  H8 ${a - H8_OFFSET:04X}  "
                  f"prior=${prior[o]:02X}")
        if len(bad_offsets) > 16:
            print(f"  ... and {len(bad_offsets) - 16} more")
        return

    os.makedirs(LOG_DIR, exist_ok=True)
    log = os.path.join(LOG_DIR, f"{datetime.date.today()}_h8-patch.log")
    t = Transport(args.dev, log)
    t.note(f"c9_h8_dump --patch {len(bad_addrs)} addrs")

    try:
        c = Consult(t)
        c.ecu_ids = ENGINE_IDS
        r = c.init()
        if r is None:
            sys.exit("init failed (ignition on?)")
        attempt, secs, junk, ecu = r
        print(f"init ok: id {ecu:02X}, attempt {attempt}, {secs * 1000:.0f} ms\n")

        patched = 0
        failed = unstable = 0
        t0 = time.monotonic()

        for i in range(0, len(bad_addrs), batch_sz):
            batch = bad_addrs[i:i + batch_sz]
            batch_n = i // batch_sz
            pct = 100 * (i + len(batch)) / len(bad_addrs)
            print(f"\r  [{batch_n + 1:3d}/{n_batches}]  "
                  f"${batch[0]:04X}–${batch[-1]:04X}  {pct:5.1f}%",
                  end="", flush=True)
            try:
                values, ok = read_forwarded(c, batch, args.frames)
                for j, addr in enumerate(batch):
                    off = all_addrs.index(addr)
                    prior[off] = values[j]
                    patched += 1
                    unstable += not ok[j]
            except (ConsultError, TimeoutError) as e:
                t.note(f"batch {batch_n} error: {e}")
                failed += 1
                try:
                    c.init()
                except Exception:
                    pass

        elapsed = time.monotonic() - t0
        print(f"\r  done: {patched}/{len(bad_addrs)} patched in {elapsed:.1f} s"
              f"          ")
        if unstable:
            print(f"  ⚠ {unstable}/{patched} re-read bytes never settled")
        if failed:
            print(f"  ⚠ {failed}/{n_batches} batches failed")
        print()

        print(f"H8 ${h8_lo:04X}–${h8_hi:04X}:")
        print(hex_dump(prior, h8_lo))

        n_zero = sum(1 for b in prior if b == 0x00)
        n_ff = sum(1 for b in prior if b == 0xFF)
        n_other = len(prior) - n_zero - n_ff
        print(f"\n  {n_zero} × $00, {n_ff} × $FF, {n_other} other")

        if args.out:
            with open(args.out, "wb") as f:
                f.write(prior)
            print(f"  saved: {args.out}")

        t.note(f"patch done: {patched} patched, {failed} failed, {elapsed:.1f} s")
    except (ConsultError, TimeoutError) as e:
        print(f"\nerror: {e}")
    finally:
        t.close()
        print(f"\nlog: {log}")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dev", default=DEFAULT_DEV,
                    help=f"serial device (default: {DEFAULT_DEV})")
    ap.add_argument("--range", default=f"{FORWARD_LO:X}-{FORWARD_HI:X}",
                    help="ECU address range in hex (default: 5D40-623F)")
    ap.add_argument("--frames", type=int, default=0,
                    help="frames to stream per batch (default: auto = 2*batch+6)")
    ap.add_argument("--batch", type=int, default=BATCH_SIZE,
                    help=f"addresses per batch (default: {BATCH_SIZE}; ≤10)")
    ap.add_argument("--patch", metavar="PRIOR.bin",
                    help="patch a prior batch-8 dump: re-read only contaminated positions")
    ap.add_argument("--out", help="save raw binary dump to file")
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would be read without talking to the ECU")
    args = ap.parse_args()

    batch_sz = min(args.batch, 10)

    lo_s, hi_s = args.range.split("-")
    lo, hi = int(lo_s, 16), int(hi_s, 16)
    if not (FORWARD_LO <= lo <= hi <= FORWARD_HI):
        sys.exit(f"range must be within ${FORWARD_LO:04X}-${FORWARD_HI:04X}")

    all_addrs = list(range(lo, hi + 1))
    h8_lo = lo - H8_OFFSET
    h8_hi = hi - H8_OFFSET

    if args.patch:
        return run_patch(args, lo, hi, h8_lo, h8_hi, all_addrs, batch_sz)

    n_batches = (len(all_addrs) + batch_sz - 1) // batch_sz

    print(f"c9_h8_dump: second CPU memory via Consult C9 forwarding")
    print(f"Target ECU: 23710-2L904 (1998 Maxima VQ30DE)")
    print(f"ECU range:  ${lo:04X}–${hi:04X} ({len(all_addrs)} bytes)")
    print(f"H8 range:   ${h8_lo:04X}–${h8_hi:04X}")
    fshow = args.frames if args.frames else f"auto(~{2 * batch_sz + 6})"
    print(f"Batches:    {n_batches} × ≤{batch_sz}, {fshow} frames each")
    print()

    if args.dry_run:
        print("(dry run — would read the above range)")
        return

    os.makedirs(LOG_DIR, exist_ok=True)
    log = os.path.join(LOG_DIR, f"{datetime.date.today()}_h8-dump.log")
    t = Transport(args.dev, log)
    t.note(f"c9_h8_dump ${lo:04X}-${hi:04X}")

    try:
        c = Consult(t)
        c.ecu_ids = ENGINE_IDS

        r = c.init()
        if r is None:
            sys.exit("init failed (ignition on?)")
        attempt, secs, junk, ecu = r
        print(f"init ok: id {ecu:02X}, attempt {attempt}, {secs * 1000:.0f} ms")
        print()

        dump = bytearray()
        status = []          # (h8_addr, ok, value)
        failed = unstable = 0
        t0 = time.monotonic()

        for i in range(0, len(all_addrs), batch_sz):
            batch = all_addrs[i:i + batch_sz]
            batch_n = i // batch_sz

            pct = 100 * (i + len(batch)) / len(all_addrs)
            print(f"\r  [{batch_n + 1:3d}/{n_batches}]  "
                  f"${batch[0]:04X}–${batch[-1]:04X}  {unstable} unstable  {pct:5.1f}%",
                  end="", flush=True)

            try:
                values, ok = read_forwarded(c, batch, args.frames)
                dump.extend(values)
                for j, addr in enumerate(batch):
                    status.append((addr - H8_OFFSET, ok[j], values[j]))
                    unstable += not ok[j]
            except (ConsultError, TimeoutError) as e:
                t.note(f"batch {batch_n} error: {e}")
                dump.extend(b"\xff" * len(batch))
                for addr in batch:
                    status.append((addr - H8_OFFSET, False, 0xFF))
                failed += 1
                try:
                    c.init()
                except Exception:
                    pass

        elapsed = time.monotonic() - t0
        print(f"\r  done: {len(dump)} bytes in {elapsed:.1f} s"
              f" ({len(dump) / elapsed:.0f} B/s)          ")
        print()

        if failed:
            print(f"  ⚠ {failed}/{n_batches} batches failed (shown as FF)")
            print()

        print(f"H8 ${h8_lo:04X}–${h8_hi:04X}:")
        print(hex_dump(dump, h8_lo))

        n_zero = sum(1 for b in dump if b == 0x00)
        n_ff = sum(1 for b in dump if b == 0xFF)
        n_other = len(dump) - n_zero - n_ff
        print(f"\n  {n_zero} × $00, {n_ff} × $FF, {n_other} other")
        print(f"  {unstable}/{len(dump)} bytes never settled (marked ?? in .txt)")

        if args.out:
            with open(args.out, "wb") as f:
                f.write(dump)
            txt = os.path.splitext(args.out)[0] + ".txt"
            with open(txt, "w") as f:
                for a, okf, v in status:
                    f.write(f"{a:04X} {'ok' if okf else '??'} {v:02X}\n")
            print(f"  saved: {args.out} (+ {txt})")

        t.note(f"done: {len(dump)} bytes, {unstable} unstable, "
               f"{failed} failed, {elapsed:.1f} s")

    except (ConsultError, TimeoutError) as e:
        print(f"\nerror: {e}")
    finally:
        t.close()
        print(f"\nlog: {log}")


if __name__ == "__main__":
    main()
