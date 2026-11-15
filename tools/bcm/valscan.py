"""Value scan on the BCM (DA): 0A <item> <xx>, never F0."""
import datetime, sys
sys.path.insert(0, ".")
from consult.transport import Transport
from consult.protocol import Consult
DA = 0xDA
items = [int(x, 16) for x in sys.argv[1:]]
log = f"logs/{datetime.date.today()}_8.0-valscan-DA.log"
t = Transport("/dev/ttyUSB0", log); c = Consult(t); c.ecu = DA; c.ecu_ids = (DA,)
def reinit():
    if c.init(DA, tries=3) is None: sys.exit("re-init failed")
    t.drain(quiet=0.1)
def send(b):
    t.write(bytes([b])); return t.read(1, timeout=0.3)
try:
    reinit(); ack = 1
    for item in items:
        hits = []
        for x in range(256):
            if ack is None: reinit()
            if send(0x0A) != b"\xf5" or send(item) != bytes([item]):
                t.note(f"valscan {item:02X} {x:02X}: prefix rejected"); ack, _ = c.stop(timeout=0.5); continue
            t.write(bytes([x])); r = t.drain(quiet=0.15, limit=0.6)
            t.note(f"valscan {item:02X} {x:02X}: rx {r.hex(' ') or '-'}")
            if r[:1] != b"\xfe": hits.append(x); print(f"  0A {item:02X} {x:02X} -> {r.hex(' ') or '-'}", flush=True)
            ack, _ = c.stop(timeout=0.5)
        print(f"{item:02X}: {len(hits)} accepted values:", " ".join(f"{x:02X}" for x in hits), flush=True)
finally:
    c.stop(timeout=0.5); t.close(); print("log:", log)
