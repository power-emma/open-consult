"""Compile and call the real C protocol with Python-controlled serial callbacks.

One client per loaded library; callbacks/globals are intentionally single-threaded.
Callback exceptions are retained and raised after returning from C, never ignored.
"""
import ctypes as c
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
WRITE = c.CFUNCTYPE(None, c.POINTER(c.c_uint8), c.c_size_t)
READ = c.CFUNCTYPE(c.c_size_t, c.POINTER(c.c_uint8), c.c_size_t, c.c_double)
NOW = c.CFUNCTYPE(c.c_double)
SLEEP = c.CFUNCTYPE(None, c.c_double)


def build_bridge(directory):
    compiler = shutil.which("cc")
    if not compiler:
        raise RuntimeError("C protocol tests require cc")
    target = Path(directory) / "consult-test.so"
    subprocess.run([
        compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC",
        "-I", str(ROOT / "src"), str(ROOT / "src/consult.c"),
        str(ROOT / "tests/harness/c_bridge.c"), "-o", str(target),
    ], check=True, capture_output=True, text=True)
    return target


class CClient:
    def __init__(self, library, wire):
        self.lib = c.CDLL(str(library))
        self.wire = wire
        self.errors = []

        def write(data, count):
            try:
                if not self.errors:
                    wire.write(c.string_at(data, count))
            except Exception as error:
                self.errors.append(error)

        def read(out, count, timeout):
            try:
                if self.errors:
                    wire.clock.sleep(timeout)
                    return 0
                data = wire.read(count, timeout)
                c.memmove(out, data, len(data))
                return len(data)
            except Exception as error:
                self.errors.append(error)
                wire.clock.sleep(timeout)
                return 0

        self.callbacks = (WRITE(write), READ(read), NOW(wire.clock.monotonic),
                          SLEEP(wire.clock.sleep))
        self.lib.bridge_bind.argtypes = [WRITE, READ, NOW, SLEEP]
        self.lib.bridge_bind(*self.callbacks)
        self.lib.bridge_memory.argtypes = [c.POINTER(c.c_uint16), c.c_int,
                                           c.POINTER(c.c_uint8)]
        self.lib.bridge_frame.argtypes = [c.c_int, c.c_double, c.POINTER(c.c_uint8)]
        self.lib.bridge_command.argtypes = [c.POINTER(c.c_uint8), c.c_size_t, c.c_int]
        self.lib.bridge_stop.argtypes = [c.c_double, c.POINTER(c.c_uint8)]

    def _check(self):
        if self.errors:
            raise self.errors[0]

    def read_memory(self, addresses):
        out = (c.c_uint8 * 255)()
        args = (c.c_uint16 * len(addresses))(*addresses)
        ok = self.lib.bridge_memory(args, len(addresses), out)
        self._check()
        if not ok:
            raise IOError("C memory read failed")
        return bytes(out[:len(addresses)])

    def read_frame(self, expected_len=None, timeout=1.0):
        out = (c.c_uint8 * 255)()
        n = self.lib.bridge_frame(-1 if expected_len is None else expected_len, timeout, out)
        self._check()
        if n < 0:
            raise TimeoutError("C frame read failed")
        return bytes(out[:n])

    def command(self, data, retries=0):
        args = (c.c_uint8 * len(data))(*data)
        ok = self.lib.bridge_command(args, len(data), retries)
        self._check()
        if not ok:
            raise IOError("C command failed")

    def stop(self, timeout=2.0):
        ack = c.c_uint8()
        ok = self.lib.bridge_stop(timeout, c.byref(ack))
        self._check()
        return (ack.value if ok else None), b""
