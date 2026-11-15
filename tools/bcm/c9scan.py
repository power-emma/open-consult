"""C9 address-echo scan on the BCM (DA): C9 <hi> <lo>, never F0. Lists the accepted lo bytes per hi."""
import datetime, sys
sys.path.insert(0, ".")
from consult.transport import Transport
from consult.protocol import Consult
DA = 0xDA
his = [int(x, 16) for x in sys.argv[1:]] or [0x80]
log = f"logs/{datetime.date.today()}_8.1-c9scan-DA.log"
t = Transport("/dev/ttyUSB0", log); c = Consult(t); c.ecu = DA; c.ecu_ids = (DA,)
def send(b):
    t.write(bytes([b])); return t.read(1, timeout=0.3)
try:
    if c.init(DA, tries=3) is None: sys.exit("init failed")
    t.drain(quiet=0.1); ack = 1
    for hi in his:
        ok = []
        for lo in range(256):
            if ack is None and c.init(DA, tries=3) is None: sys.exit("re-init failed")
            e1 = send(0xC9); e2 = send(hi) if e1 == b"\x36" else b""
            if e2 != bytes([hi]):
                t.note(f"c9scan {hi:02X}{lo:02X}: prefix {e1.hex()} {e2.hex()}"); ack, _ = c.stop(0.5); continue
            r = send(lo)
            t.note(f"c9scan {hi:02X}{lo:02X}: {r.hex() or '-'}")
            if r == bytes([lo]): ok.append(lo)
            ack, _ = c.stop(0.5)
        print(f"hi {hi:02X}: {len(ok)} accepted lo:", " ".join(f"{x:02X}" for x in ok), flush=True)
finally:
    c.stop(0.5); t.close(); print("log:", log)
