"""Fire BCM (DA) active tests: 0A <item> <value> F0, hold, 30. One at a time."""
import datetime, sys, time
sys.path.insert(0, ".")
from consult.transport import Transport
from consult.protocol import Consult
DA = 0xDA
value = int(sys.argv[1], 16); hold = float(sys.argv[2]); start = float(sys.argv[3]); gap = float(sys.argv[4]); items = [int(x, 16) for x in sys.argv[5:]]
log = f"logs/{datetime.date.today()}_8.x-fire-DA.log"
t = Transport("/dev/ttyUSB0", log); c = Consult(t); c.ecu = DA; c.ecu_ids = (DA,)
def send(b):
    t.write(bytes([b])); return t.read(1, timeout=0.3)
try:
    for k, item in enumerate(items):
        time.sleep(max(0, start + k * gap - 1.0 - time.time()))
        if c.init(DA, tries=3) is None: sys.exit("init failed")
        t.drain(quiet=0.1)
        if send(0x0A) != b"\xf5" or send(item) != bytes([item]) or send(value) != bytes([value]):
            print(f"{datetime.datetime.now():%H:%M:%S} {item:02X}: echo rejected", flush=True); c.stop(0.5); continue
        t.note(f"FIRE 0A {item:02X} {value:02X} F0")
        time.sleep(max(0, start + k * gap - time.time()))
        t.write(b"\xf0")
        print(f"{datetime.datetime.now():%H:%M:%S} FIRE {item:02X}", flush=True)
        rx = t.drain(quiet=hold, limit=hold)
        ack, _ = c.stop(timeout=1.0)
        print(f"   rx {rx[:24].hex(' ') or '-'}{' …' if len(rx) > 24 else ''}; stop ack {ack if ack is None else f'{ack:02X}'}", flush=True)
        t.note(f"fired {item:02X} rx={rx.hex(' ')} ack={ack}")
finally:
    c.stop(timeout=0.5); t.close(); print("log:", log)
