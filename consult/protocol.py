"""Consult-I protocol layer (CONSULT_PROTOCOL.md §4–5).

Only the read-side commands live here for now. Active tests (0A) and DTC clear (C1)
are left out on purpose until the link basics are verified on the car.
"""
import time

ENGINE = 0xEF
STOP = 0x30
GO = 0xF0
STOP_ACKS = (0xCF, 0xFE)        # spec says CF, Nissboard saw FE (§12 #1)

# Number of argument bytes that follow each command byte (echoed verbatim).
NARGS = {0x5A: 1, 0xC9: 2, 0x0A: 2}


class ConsultError(IOError):
    pass


def expected_echo(payload: bytes) -> bytes:
    out = bytearray()
    i = 0
    while i < len(payload):
        cmd = payload[i]
        n = NARGS.get(cmd, 0)
        out.append(~cmd & 0xFF)
        out += payload[i + 1:i + 1 + n]
        i += 1 + n
    return bytes(out)


class Consult:
    def __init__(self, transport):
        self.t = transport

    def stop(self, timeout=2.0):
        """Send 30 and read until a stop ack. Returns (ack byte or None, bytes before it)."""
        self.t.write(bytes([STOP]))
        before = bytearray()
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            b = self.t.read(1, timeout=0.3)
            if not b:
                continue
            if b[0] in STOP_ACKS:
                return b[0], bytes(before)
            before += b
        return None, bytes(before)

    def init(self, ecu=ENGINE, tries=5, wait=2.0, pre_stop=True):
        """Send FF FF <ecu> until 0x10 comes back.

        Returns (attempt number, seconds from TX to the 0x10, other bytes seen) on
        success, or None.
        """
        for attempt in range(1, tries + 1):
            if pre_stop:
                self.stop(timeout=0.5)
                self.t.drain(quiet=0.2)
            self.t.write(bytes([0xFF, 0xFF, ecu]))
            sent = time.monotonic()
            junk = bytearray()
            while time.monotonic() - sent < wait:
                b = self.t.read(1, timeout=0.2)
                if not b:
                    continue
                if b[0] == 0x10:
                    return attempt, time.monotonic() - sent, bytes(junk)
                junk += b
        return None

    def command(self, payload: bytes):
        """Send a command list, check the echo, then send F0 to start streaming."""
        self.t.write(payload)
        want = expected_echo(payload)
        got = self.t.read(len(want), timeout=0.5)
        if got != want:
            self.stop(timeout=0.5)
            raise ConsultError(f"bad echo {got.hex(' ') or '(none)'}, expected {want.hex(' ')}")
        self.t.write(bytes([GO]))

    def read_frame(self, expected_len=None, timeout=1.0) -> bytes:
        """Read one FF <n> <data...> frame, parsing by length (data may contain FF)."""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            b = self.t.read(1, timeout=timeout)
            if not b:
                break
            if b[0] != 0xFF:
                continue
            n = self.t.read(1, timeout=0.3)
            if not n:
                break
            n = n[0]
            if expected_len is not None and n != expected_len:
                continue
            data = self.t.read(n, timeout=0.3)
            if len(data) == n:
                return data
        raise TimeoutError("no frame")

    def one_shot(self, payload: bytes, expected_len=None) -> bytes:
        """Command, read a single frame, stop."""
        self.command(payload)
        try:
            return self.read_frame(expected_len)
        finally:
            self.stop()

    def read_registers(self, regs):
        return b"".join(bytes([0x5A, r]) for r in regs)

    def part_number(self):
        d = self.one_shot(bytes([0xD0]))
        pn = None
        if len(d) >= 22:
            pn = f"{d[2]:02X}{d[3]:02X} 23710-{d[19]:X}{d[20]:02X}{d[21]:02X}"
        return d, pn

    def dtcs(self):
        d = self.one_shot(bytes([0xD1]))
        return d, [(d[i], d[i + 1]) for i in range(0, len(d) - 1, 2)]
