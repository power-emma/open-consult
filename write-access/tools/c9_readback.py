#!/usr/bin/env python3
"""Read a RAM address N times, one init/read/stop per loop."""
import argparse, os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from consult.protocol import Consult, ENGINE_IDS
from consult.transport import DEFAULT_DEV, Transport

ap = argparse.ArgumentParser()
ap.add_argument("--target", type=lambda x: int(x, 16), default=0x0817)
ap.add_argument("-n", type=int, default=10)
ap.add_argument("--dev", default=DEFAULT_DEV)
args = ap.parse_args()

t = Transport(args.dev)
c = Consult(t)
c.ecu_ids = ENGINE_IDS
for i in range(args.n):
    r = c.init()
    if r is None:
        print(f"  {i}: init failed"); continue
    v = c.read_memory([args.target])[0]
    print(f"  {i}: ${v:02X}")
    c.stop()
    time.sleep(0.3)
t.close()
