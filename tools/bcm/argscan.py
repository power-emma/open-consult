"""Argument scan on the BCM (DA): <cmd> <xx>, never F0. Prints which xx are echoed."""
import datetime, os, sys, time
sys.path.insert(0, ".")
from consult.transport import Transport
from consult.protocol import Consult

DA = 0xDA
cmds = [int(x, 16) for x in sys.argv[1:]] or [0x0A, 0x9E]
log = f"logs/{datetime.date.today()}_8.0-argscan-DA.log"
t = Transport("/dev/ttyUSB0", log)
c = Consult(t)
c.ecu = DA
c.ecu_ids = (DA,)

def reinit():
    if c.init(DA, tries=3) is None:
        sys.exit("re-init failed")
    t.drain(quiet=0.1)

try:
    reinit()
    for cmd in cmds:
        t.note(f"argscan {cmd:02X}")
        t.write(bytes([cmd]))
        e = t.read(1, timeout=0.3)
        print(f"{cmd:02X} alone -> {e.hex() or '-'} (echo would be {~cmd & 0xFF:02X})", flush=True)
        ack, _ = c.stop(timeout=0.5)
        if e != bytes([~cmd & 0xFF]):
            continue
        hits = []
        for x in range(256):
            if ack is None:
                reinit()
            t.write(bytes([cmd]))
            e = t.read(1, timeout=0.3)
            if e != bytes([~cmd & 0xFF]):
                t.note(f"argscan {cmd:02X} {x:02X}: cmd echo {e.hex() or '-'}")
                ack, _ = c.stop(timeout=0.5)
                continue
            t.write(bytes([x]))
            r = t.drain(quiet=0.15, limit=0.6)
            t.note(f"argscan {cmd:02X} {x:02X}: rx {r.hex(' ') or '-'}")
            if r[:1] != b"\xfe":
                hits.append((x, r))
                print(f"  {cmd:02X} {x:02X} -> {r.hex(' ') or '-'}", flush=True)
            ack, _ = c.stop(timeout=0.5)
        print(f"{cmd:02X}: {len(hits)} non-FE args:", " ".join(f"{x:02X}" for x, _ in hits), flush=True)
finally:
    c.stop(timeout=0.5)
    t.close()
    print("log:", log)
