"""probe: read-only Consult test tool for CAR_TEST_CHECKLIST.md sections 1–3.

    python -m consult init                  # 1.1
    python -m consult stop-ack              # 1.5
    python -m consult id                    # 2.1 / 2.2
    python -m consult dtc                   # 2.3
    python -m consult watch rpm coolant     # live data
    python -m consult reg-scan              # 3.1 / 3.2
    python -m consult active fan-low        # 4.x (changes engine behaviour)
    python -m consult mem 8000 -n 16        # 5.1 / 5.5
    python -m consult rom-dump              # 5.3 / 5.4, to rom/<part number>.bin

Every run appends a raw TX/RX log to logs/YYYY-MM-DD_<test-id>.log.
"""
import argparse
import datetime
import hashlib
import os
import sys
import time

from .dtcs import describe
from .protocol import ENGINE_IDS, STOP_ACKS, Consult, ConsultError
from .registers import ENGINE, decode, registers_for
from .transport import DEFAULT_DEV, Transport

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(ROOT, "logs")
AIRBAG = 0xDC   # 1998 Maxima: init + C9 to DC blinked the AIR BAG lamp (2026-11-14)
ROM_DIR = os.path.join(ROOT, "rom")


def connect(c):
    r = c.init(c.ecu_ids)
    if r is None:
        sys.exit("init failed: no reply from the ECU (ignition on? dongle in the car?)")
    attempt, secs, junk, ecu = r
    print(f"init ok: id {ecu:02X}, attempt {attempt}, {~ecu & 0xFF:02X} after "
          f"{secs * 1000:.0f} ms" + (f", other bytes first: {junk.hex(' ')}" if junk else ""))
    c.t.note(f"init ok id={ecu:02X} attempt={attempt} secs={secs:.3f}")


def cmd_init(c, args):
    connect(c)


def parse_gaps(text):
    if text == "none":
        return None
    a, b = (float(v) for v in text.split(","))
    return a, b


def cmd_init_scan(c, args):
    """6.2: FF FF xx for each xx, logging any reply. Read-only (init bytes only)."""
    hits = []
    c.t.note(f"gaps {args.gaps}")
    for x in range(args.first, args.last + 1):
        if x == AIRBAG:
            continue
        c.stop(timeout=0.3)
        c.t.drain(quiet=0.2)
        c.t.note(f"scan {x:02X}")
        if args.gaps is None:
            c.t.write(bytes([0xFF, 0xFF, x]))
        else:
            c.t.write(b"\xFF")
            time.sleep(args.gaps[0])
            c.t.write(b"\xFF")
            time.sleep(args.gaps[1])
            c.t.write(bytes([x]))
        rx = c.t.drain(quiet=args.wait, limit=args.wait + 1.0)
        if rx:
            tag = "complement" if rx[0] == ~x & 0xFF else "other"
            hits.append((x, rx, tag))
            print(f"  {x:02X}: {rx[:16].hex(' ')} ({tag})", flush=True)
            c.t.note(f"hit {x:02X} rx={rx.hex(' ')} {tag}")
        elif x % 16 == 15:
            print(f"  ..{x:02X} scanned", flush=True)
    c.stop(timeout=0.3)
    print("hits:", " ".join(f"{x:02X}->{rx[0]:02X}" for x, rx, _ in hits) or "none")


CMD_PROBE_SKIP = {0x30, 0xF0, 0xFF, 0x0A, 0xC1}


def cmd_cmd_probe(c, args):
    """Send each command byte alone (never F0) and classify the reply.

    Re-inits before every byte so a command still waiting for its arguments can't
    take the next probe byte as one.
    """
    found = {"echo": [], "fe": [], "silent": [], "other": []}
    for x in range(args.first, args.last + 1):
        if x in CMD_PROBE_SKIP:
            continue
        if c.init(c.ecu_ids, tries=2) is None:
            print(f"  {x:02X}: re-init failed, stopping")
            break
        c.t.drain(quiet=0.1)
        c.t.note(f"probe {x:02X}")
        c.t.write(bytes([x]))
        rx = c.t.drain(quiet=0.3, limit=1.0)
        kind = ("silent" if not rx else "echo" if rx[0] == ~x & 0xFF
                else "fe" if set(rx) == {0xFE} else "other")
        found[kind].append(x)
        if kind in ("echo", "other") or args.verbose:
            print(f"  {x:02X}: {rx.hex(' ') or '-'} ({kind})", flush=True)
        c.t.note(f"probe {x:02X} rx={rx.hex(' ')} {kind}")
        c.stop(timeout=0.3)
    for k, v in found.items():
        print(f"{k} ({len(v)}):", " ".join(f"{x:02X}" for x in v))


def cmd_stop_ack(c, args):
    connect(c)
    c.command(bytes([0x5A, 0x0C]))
    for _ in range(5):
        c.read_frame(1)
    ack, before = c.stop()
    print(f"stop ack: {f'{ack:02X}' if ack is not None else 'NONE'}; "
          f"{len(before)} byte(s) before it: {before.hex(' ') or '-'}")


def cmd_id(c, args):
    connect(c)
    d, pn = c.part_number()
    print(f"D0 raw ({len(d)} bytes): {d.hex(' ')}")
    print(f"part number: {pn}")
    print("as ASCII:", "".join(chr(b) if 32 <= b < 127 else "." for b in d))


def cmd_dtc(c, args):
    connect(c)
    d, codes = c.dtcs()
    print(f"D1 raw ({len(d)} bytes): {d.hex(' ')}")
    for code, starts in codes:
        print(f"  {code:02X}  {describe(code)}, starts byte {starts}")


def cmd_watch(c, args):
    names = args.names or ["rpm", "coolant", "battery", "tps"]
    for n in names:
        if n not in ENGINE:
            sys.exit(f"unknown register '{n}'. Known: {', '.join(ENGINE)}")
    regs = registers_for(names)
    connect(c)
    c.command(b"".join(bytes([0x5A, r]) for r in regs))
    frames, t0 = 0, time.monotonic()
    try:
        while args.count == 0 or frames < args.count:
            vals = decode(names, c.read_frame(len(regs)))
            frames += 1
            rate = frames / (time.monotonic() - t0)
            print("  ".join(f"{n}={v}{u}" for n, (v, u) in vals.items()) + f"  [{rate:.1f} fps]")
    except KeyboardInterrupt:
        pass
    finally:
        c.stop()


def cmd_watch_raw(c, args):
    """Stream raw registers (any unit) and print a line only when a byte changes."""
    regs = [int(r, 16) for r in args.regs]
    connect(c)
    # The BCM takes one register per request (a second 5A gets FE), so poll in turn.
    poll = c.paced and len(regs) > 1
    if not poll:
        c.command(b"".join(bytes([0x5A, r]) for r in regs))
    last, t0 = None, time.monotonic()
    try:
        while True:
            parts = ([c.one_shot(bytes([0x5A, r])) for r in regs] if poll
                     else [c.read_frame()])
            f = b"".join(parts)
            names = ([f"{r:02X}+{i}" for r, p in zip(regs, parts) for i in range(len(p))]
                     if poll else [str(i) for i in range(len(f))])
            if f != last:
                diff = "" if last is None or len(last) != len(f) else "  changed: " + " ".join(
                    f"{names[i]} {a:02X}->{b:02X}" for i, (a, b) in enumerate(zip(last, f)) if a != b)
                print(f"{time.monotonic() - t0:7.2f}s  {f.hex(' ')}{diff}", flush=True)
                c.t.note(f"frame {f.hex(' ')}")
                last = f
    except KeyboardInterrupt:
        pass
    finally:
        c.stop()


def cmd_watch_mem(c, args):
    """Poll a C9 address range and print a line whenever a byte changes."""
    addrs = list(range(args.addr, args.addr + args.count))
    connect(c)
    step = 6 if c.paced else 8      # the BCM answers FE to a 7th address (2026-11-14)
    last, t0, sweeps = None, time.monotonic(), 0
    try:
        while True:
            cur = b"".join(c.read_memory(addrs[i:i + step]) for i in range(0, len(addrs), step))
            sweeps += 1
            if last is None:
                print(f"{time.monotonic() - t0:7.2f}s  baseline {addrs[0]:04X}: {cur.hex(' ')}", flush=True)
            elif cur != last:
                print(f"{time.monotonic() - t0:7.2f}s  " + " ".join(
                    f"{addrs[i]:04X} {a:02X}->{b:02X}" for i, (a, b) in enumerate(zip(last, cur))
                    if a != b), flush=True)
            if cur != last:
                c.t.note(f"mem {cur.hex(' ')}")
            last = cur
    except KeyboardInterrupt:
        pass
    finally:
        c.stop()
        secs = time.monotonic() - t0
        print(f"{sweeps} sweeps in {secs:.0f} s ({secs / max(sweeps, 1):.2f} s each)")


def cmd_reg_scan(c, args):
    connect(c)
    supported = []
    for r in range(args.first, args.last + 1):
        try:
            v = c.one_shot(bytes([0x5A, r]), expected_len=1)
            supported.append(r)
            print(f"  {r:02X}: supported, value {v[0]:02X}")
            c.t.note(f"reg {r:02X} supported value={v[0]:02X}")
        except (ConsultError, TimeoutError) as e:
            c.t.note(f"reg {r:02X} unsupported: {e}")
            if args.verbose:
                print(f"  {r:02X}: {e}")
            c.t.drain(quiet=0.2)
    print("supported:", " ".join(f"{r:02X}" for r in supported))


def cmd_mem(c, args):
    connect(c)
    addrs = list(range(args.addr, args.addr + args.count))
    for n in range(args.repeat):
        for i in range(0, len(addrs), 8):
            d = c.read_memory(addrs[i:i + 8])
            print(f"{addrs[i]:04X}: {d.hex(' ')}")
        if args.repeat > 1:
            print()


def cmd_rom_dump(c, args):
    """C9 in 8-byte requests over first..last, written as it goes so --resume works."""
    connect(c)
    first, last = args.first, args.last
    if args.output:
        out = args.output
    else:
        _, pn = c.part_number()
        os.makedirs(ROM_DIR, exist_ok=True)
        out = os.path.join(ROM_DIR, f"{pn or 'unknown'}_{first:04X}-{last:04X}.bin")
    done = os.path.getsize(out) if args.resume and os.path.exists(out) else 0
    size = last - first + 1
    if done > size:
        sys.exit(f"{out} is already larger than {size} bytes")
    print(f"dumping {first:04X}-{last:04X} to {out}" + (f", resuming at {first + done:04X}" if done else ""))
    t0 = time.monotonic()
    with open(out, "ab" if done else "wb") as f:
        addr = first + done
        while addr <= last:
            chunk = list(range(addr, min(addr + 8, last + 1)))
            for attempt in range(3):
                try:
                    d = c.read_memory(chunk)
                    break
                except (ConsultError, TimeoutError) as e:
                    c.t.note(f"C9 at {addr:04X} try {attempt + 1} failed: {e}")
                    c.stop(timeout=0.5)
                    c.t.drain(quiet=0.1)
            else:
                raise ConsultError(f"read at {addr:04X} failed 3 times; rerun with --resume")
            f.write(d)
            f.flush()
            addr += len(chunk)
            if (addr - first) % 0x400 == 0 or addr > last:
                secs = time.monotonic() - t0
                left = (last + 1 - addr) * secs / max(addr - first - done, 1)
                print(f"\r  {addr - first:5d}/{size} bytes, {secs:4.0f} s, ~{left:4.0f} s left",
                      end="", flush=True)
    print()
    with open(out, "rb") as f:
        data = f.read()
    print(f"done: {len(data)} bytes in {time.monotonic() - t0:.0f} s, "
          f"sha256 {hashlib.sha256(data).hexdigest()}")
    c.t.note(f"rom-dump {out} {len(data)} bytes sha256={hashlib.sha256(data).hexdigest()}")


def cmd_sub_dump(c, args):
    """C9 on the range the ECU forwards to its second processor (ROM_ANALYSIS.md §6).

    For C9 addresses $5D40-$623F the ECU doesn't read its own memory: it passes
    (address - $5000) to the other CPU and fills the byte from that CPU's reply, one
    per frame, starting with the second frame. So each address is streamed for
    `--frames` frames and the value is kept only when the later frames agree.
    Read-only. Output: rom/sub_<first-5000>-<last-5000>.bin and a .txt of each
    address's frames, so unstable bytes can be checked.
    """
    connect(c)
    first, last = args.first, args.last
    os.makedirs(ROM_DIR, exist_ok=True)
    base = os.path.join(ROM_DIR, f"sub_{first - 0x5000:04X}-{last - 0x5000:04X}")
    data, unstable, t0 = bytearray(), 0, time.monotonic()
    with open(base + ".txt", "w") as txt:
        for addr in range(first, last + 1):
            frames = []
            try:
                c.command(bytes([0xC9, addr >> 8, addr & 0xFF]))
                for _ in range(args.frames):
                    frames.append(c.read_frame(expected_len=1)[0])
            except (ConsultError, TimeoutError) as e:
                c.t.note(f"sub {addr:04X} failed: {e}")
            finally:
                c.stop(timeout=0.5)
                c.t.drain(quiet=0.05)
            late = frames[len(frames) // 2:]
            ok = len(late) >= 2 and len(set(late)) == 1
            unstable += not ok
            data.append(late[-1] if late else 0)
            txt.write(f"{addr - 0x5000:04X} {'ok ' if ok else '?? '}{' '.join(f'{v:02X}' for v in frames)}\n")
            c.t.note(f"sub {addr - 0x5000:04X} frames {' '.join(f'{v:02X}' for v in frames)}")
            if (addr - first) % 64 == 63:
                print(f"\r  {addr - first + 1}/{last - first + 1}, {unstable} unstable, "
                      f"{time.monotonic() - t0:.0f} s", end="", flush=True)
    print()
    with open(base + ".bin", "wb") as f:
        f.write(data)
    print(f"wrote {base}.bin ({len(data)} bytes, {unstable} unstable; see {base}.txt)")


# Active tests (CONSULT_PROTOCOL.md §8), with limits kept inside the normal ranges.
# name -> (test register, argument help, argument -> value byte, needs the engine running)
ACTIVE_TESTS = {
    "fan-low":      (0x93, None, lambda a: 0x01, False),
    "fan-high":     (0x94, None, lambda a: 0x01, False),
    "coolant":      (0x80, "°C, 20..110", lambda a: _ranged(a, 20, 110) + 50, False),
    "fuel-trim":    (0x81, "percent, -10..+10", lambda a: 0x64 + _ranged(a, -10, 10), True),
    "timing":       (0x82, "degrees, -5..+5", lambda a: _ranged(a, -5, 5) & 0xFF, True),
    # Bitmask per Issue 6 (bit 0 = cylinder 1). For cylinders 1 and 2 the bitmask and
    # the cylinder-number encoding give the same byte, so those are safe either way.
    "cut-cylinder": (0x88, "cylinder, 1..6", lambda a: 1 << (_ranged(a, 1, 6) - 1), True),
}
SNAPSHOT = ["rpm", "coolant", "timing", "inj_lh", "inj_rh", "o2_lh", "o2_rh", "bits1e"]


def _ranged(arg, lo, hi):
    if arg is None:
        raise ValueError(f"needs a value ({lo}..{hi})")
    v = int(arg)
    if not lo <= v <= hi:
        raise ValueError(f"{v} is outside {lo}..{hi}")
    return v


def snapshot(c, frames=5):
    """Stream a few frames of SNAPSHOT and return the last one decoded."""
    regs = registers_for(SNAPSHOT)
    c.command(b"".join(bytes([0x5A, r]) for r in regs))
    try:
        for _ in range(frames):
            vals = decode(SNAPSHOT, c.read_frame(len(regs)))
    finally:
        c.stop()
    return vals


def fmt(vals):
    return "  ".join(f"{n}={v}{u}" for n, (v, u) in vals.items())


def cmd_raw_cmd(c, args):
    """Send arbitrary bytes after init and log whatever comes back."""
    connect(c)
    payload = bytes.fromhex(args.hex.replace(" ", ""))
    print(f"sending {payload.hex(' ')} ({len(payload)} bytes)")
    c.t.write(payload)
    time.sleep(0.5)
    rx = c.t.read(64, timeout=1.0)
    print(f"received {len(rx)} byte(s): {rx.hex(' ') if rx else '(none)'}")
    c.t.note(f"raw-cmd tx={payload.hex(' ')} rx={rx.hex(' ') if rx else '(none)'}")
    c.stop(timeout=0.5)


def cmd_active(c, args):
    test, arg_help, encode, needs_running = ACTIVE_TESTS[args.test]
    try:
        value = encode(args.value)
    except ValueError as e:
        sys.exit(f"{args.test}: {e}")
    hold = min(args.hold, 30.0)
    connect(c)
    before = snapshot(c)
    print("before:", fmt(before))
    rpm, coolant = before["rpm"][0], before["coolant"][0]
    if needs_running and not 400 <= rpm <= 1500:
        sys.exit(f"{args.test} needs the engine idling (rpm {rpm:.0f}); not sent")
    if args.test == "cut-cylinder" and coolant < 60:
        sys.exit(f"cut-cylinder needs a warm engine (coolant {coolant} °C); not sent")
    if not args.yes:
        ok = input("Parked, handbrake on, in neutral, hands clear of the fan and belts? [y/N] ")
        if ok.strip().lower() != "y":
            sys.exit("not sent")
    print(f"sending 0A {test:02X} {value:02X}, holding {hold:.0f} s (Ctrl-C stops it early)")
    try:
        rx, ack = c.active_test(test, value, hold,
                                on_rx=lambda b: print("  rx:", b.hex(" ")) if args.verbose else None)
    except KeyboardInterrupt:
        rx, ack = b"", None
    print(f"during the test the ECU sent {len(rx)} byte(s)" + (f": {rx[:32].hex(' ')}"
          + (" …" if len(rx) > 32 else "") if rx else ""))
    if ack not in STOP_ACKS:
        print("WARNING: no stop ack. Turn the key off to be sure the test has ended.")
    else:
        print(f"stopped (ack {ack:02X})")
    print("after: ", fmt(snapshot(c)))


def main():
    ap = argparse.ArgumentParser(prog="probe", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dev", default=DEFAULT_DEV)
    ap.add_argument("--test-id", help="log name suffix, e.g. 1.1 (default: subcommand)")
    ap.add_argument("--ecu", type=lambda x: int(x, 16), action="append",
                    help="init ID in hex, repeatable (default: ED then EF)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sc = sub.add_parser("init-scan", help="6.2: try FF FF xx for every xx, list replies")
    sc.add_argument("--first", type=lambda x: int(x, 16), default=0x00)
    sc.add_argument("--last", type=lambda x: int(x, 16), default=0xFF)
    sc.add_argument("--wait", type=float, default=0.5, help="seconds of silence per ID")
    sc.add_argument("--gaps", type=parse_gaps, default=(0.28, 0.07),
                    help="pauses after each FF: 'none' = back to back, or 'A,B' in seconds "
                         "(default 0.28,0.07 = ECUTalk)")
    cp = sub.add_parser("cmd-probe", help="send each command byte without F0, list echoes")
    cp.add_argument("--first", type=lambda x: int(x, 16), default=0x00)
    cp.add_argument("--last", type=lambda x: int(x, 16), default=0xFF)
    cp.add_argument("-v", "--verbose", action="store_true")
    sub.add_parser("stop-ack")
    sub.add_parser("id")
    sub.add_parser("dtc")
    w = sub.add_parser("watch")
    w.add_argument("names", nargs="*")
    w.add_argument("-n", "--count", type=int, default=0, help="frames to read (0 = until Ctrl-C)")
    wr = sub.add_parser("watch-raw", help="stream raw registers, print changes (e.g. --ecu DC)")
    wr.add_argument("regs", nargs="+", help="register numbers in hex, e.g. 8A AB")
    wm = sub.add_parser("watch-mem", help="poll C9 addresses, print changes (BCM: FF00 -n 96)")
    wm.add_argument("addr", type=lambda x: int(x, 16))
    wm.add_argument("-n", "--count", type=int, default=96)
    s = sub.add_parser("reg-scan")
    s.add_argument("--first", type=lambda x: int(x, 16), default=0x00)
    s.add_argument("--last", type=lambda x: int(x, 16), default=0xFF)
    s.add_argument("-v", "--verbose", action="store_true")
    rc = sub.add_parser("raw-cmd", help="send raw hex bytes after init and log the reply")
    rc.add_argument("hex", help="hex bytes to send, e.g. '5B' or '5A 0C'")
    a = sub.add_parser("active", help="active test: CHANGES ENGINE BEHAVIOUR")
    a.add_argument("test", choices=ACTIVE_TESTS)
    a.add_argument("value", nargs="?", help="; ".join(
        f"{k}: {v[1]}" for k, v in ACTIVE_TESTS.items() if v[1]))
    a.add_argument("--hold", type=float, default=5.0, help="seconds, max 30 (default 5)")
    a.add_argument("-y", "--yes", action="store_true", help="skip the safety prompt")
    a.add_argument("-v", "--verbose", action="store_true", help="print bytes during the test")
    hexint = lambda x: int(x, 16)
    m = sub.add_parser("mem", help="C9: read ROM/RAM bytes")
    m.add_argument("addr", type=hexint)
    m.add_argument("-n", "--count", type=int, default=8)
    m.add_argument("-r", "--repeat", type=int, default=1, help="read it this many times")
    sd = sub.add_parser("sub-dump", help="C9 $5D40-$623F: read the second CPU's memory")
    sd.add_argument("--first", type=lambda x: int(x, 16), default=0x5D40)
    sd.add_argument("--last", type=lambda x: int(x, 16), default=0x623F)
    sd.add_argument("--frames", type=int, default=6, help="frames to read per address")
    r = sub.add_parser("rom-dump", help="C9: dump ROM to a file")
    r.add_argument("--first", type=hexint, default=0x8000)
    r.add_argument("--last", type=hexint, default=0xFFFF)
    r.add_argument("-o", "--output")
    r.add_argument("--resume", action="store_true", help="append to an existing partial dump")
    args = ap.parse_args()
    if args.ecu and AIRBAG in args.ecu:
        sys.exit(f"{AIRBAG:02X} is the airbag (SRS) unit: addressing it blinks the AIR BAG lamp. Not sent.")
    if args.cmd == "active" and args.ecu and set(args.ecu) - set(ENGINE_IDS):
        sys.exit("active tests are engine-only (on E7, the ABS, 0A drives the brake valves and pump)")

    os.makedirs(LOG_DIR, exist_ok=True)
    log = os.path.join(LOG_DIR, f"{datetime.date.today()}_{args.test_id or args.cmd}.log")
    try:
        t = Transport(args.dev, log)
    except (PermissionError, IOError) as e:
        if os.name == "nt":
            if "denied" not in str(e).lower():
                sys.exit(f"cannot open {args.dev}: {e}")
            sys.exit(f"{args.dev} is busy or access denied: close ECUTalk or anything else using it")
        sys.exit(f"no permission for {args.dev}: run `sudo usermod -aG uucp $USER`, "
                 "then log out and back in (or `newgrp uucp`)")
    t.note("cmd: " + " ".join(sys.argv[1:]))
    try:
        c = Consult(t)
        c.ecu_ids = tuple(args.ecu) if args.ecu else ENGINE_IDS
        globals()["cmd_" + args.cmd.replace("-", "_")](c, args)
    except (ConsultError, TimeoutError) as e:
        print("error:", e)
    finally:
        t.close()
        print(f"log: {log}")


if __name__ == "__main__":
    main()
