"""probe: read-only Consult test tool for CAR_TEST_CHECKLIST.md sections 1–3.

    python -m consult init                  # 1.1
    python -m consult stop-ack              # 1.5
    python -m consult id                    # 2.1 / 2.2
    python -m consult dtc                   # 2.3
    python -m consult watch rpm coolant     # live data
    python -m consult reg-scan              # 3.1 / 3.2

Every run appends a raw TX/RX log to logs/YYYY-MM-DD_<test-id>.log.
"""
import argparse
import datetime
import os
import sys
import time

from .protocol import Consult, ConsultError
from .registers import ENGINE, decode, registers_for
from .transport import DEFAULT_DEV, Transport

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")


def connect(c):
    r = c.init()
    if r is None:
        sys.exit("init failed: no 0x10 from the ECU (ignition on? dongle in the car?)")
    attempt, secs, junk = r
    print(f"init ok: attempt {attempt}, 0x10 after {secs * 1000:.0f} ms"
          + (f", other bytes first: {junk.hex(' ')}" if junk else ""))
    c.t.note(f"init ok attempt={attempt} secs={secs:.3f}")


def cmd_init(c, args):
    connect(c)


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
    print(f"part number (openconsult decoding): {pn}")
    print("as ASCII:", "".join(chr(b) if 32 <= b < 127 else "." for b in d))


def cmd_dtc(c, args):
    connect(c)
    d, codes = c.dtcs()
    print(f"D1 raw ({len(d)} bytes): {d.hex(' ')}")
    for code, starts in codes:
        print(f"  code byte 0x{code:02X} (hex-digit '{code:02X}', decimal {code}), "
              f"starts since last seen: {starts}")


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


def main():
    ap = argparse.ArgumentParser(prog="probe", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dev", default=DEFAULT_DEV)
    ap.add_argument("--test-id", help="log name suffix, e.g. 1.1 (default: subcommand)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("stop-ack")
    sub.add_parser("id")
    sub.add_parser("dtc")
    w = sub.add_parser("watch")
    w.add_argument("names", nargs="*")
    w.add_argument("-n", "--count", type=int, default=0, help="frames to read (0 = until Ctrl-C)")
    s = sub.add_parser("reg-scan")
    s.add_argument("--first", type=lambda x: int(x, 16), default=0x00)
    s.add_argument("--last", type=lambda x: int(x, 16), default=0xFF)
    s.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    os.makedirs(LOG_DIR, exist_ok=True)
    log = os.path.join(LOG_DIR, f"{datetime.date.today()}_{args.test_id or args.cmd}.log")
    try:
        t = Transport(args.dev, log)
    except PermissionError:
        if os.name == "nt":
            sys.exit(f"{args.dev} is busy or access denied: close ECUTalk or anything else using it")
        sys.exit(f"no permission for {args.dev}: run `sudo usermod -aG uucp $USER`, "
                 "then log out and back in (or `newgrp uucp`)")
    t.note("cmd: " + " ".join(sys.argv[1:]))
    try:
        globals()["cmd_" + args.cmd.replace("-", "_")](Consult(t), args)
    except (ConsultError, TimeoutError) as e:
        print("error:", e)
    finally:
        t.close()
        print(f"log: {log}")


if __name__ == "__main__":
    main()
