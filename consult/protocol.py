"""Consult-I protocol layer (CONSULT_PROTOCOL.md §4–5).

Only the read-side commands live here for now. Active tests (0A) and DTC clear (C1)
are left out on purpose until the link basics are verified on the car.
"""
import time

ENGINE = 0xEF
ENGINE_ALT = 0xED               # the 1998 Maxima's engine ECU answers ED (reply 12), not EF
ENGINE_IDS = (ENGINE_ALT, ENGINE)
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

    def init(self, ecu=ENGINE_IDS, tries=5, wait=2.0, pre_stop=True, gaps=(0.28, 0.07)):
        """Send FF FF <ecu> until ~ecu (10 for EF, 12 for ED) comes back.

        `ecu` is one ID or a sequence of IDs tried in turn on each attempt. The
        default tries ED first and then EF: the 1998 Maxima answers ED. After a
        wrong-ID init the ECU ignores everything, including 30, until it gets a
        correct init.

        `gaps` are the pauses after the first and second FF. ECUTalk 1.5.0 sends the
        three bytes separately with Sleep(Delay1=280 ms) and Sleep(Delay2=70 ms) in
        between (decompiled, see HANDOFF.md). Pass gaps=None to send them back to back.

        Returns (attempt number, seconds from TX to the reply, other bytes seen, id)
        on success, or None.
        """
        ids = (ecu,) if isinstance(ecu, int) else tuple(ecu)
        for n in range(tries * len(ids)):
            attempt, ecu = n // len(ids) + 1, ids[n % len(ids)]
            if pre_stop:
                self.stop(timeout=0.5)
                self.t.drain(quiet=0.2)
            if gaps:
                self.t.write(b"\xFF")
                time.sleep(gaps[0])
                self.t.write(b"\xFF")
                time.sleep(gaps[1])
                self.t.write(bytes([ecu]))
            else:
                self.t.write(bytes([0xFF, 0xFF, ecu]))
            sent = time.monotonic()
            junk = bytearray()
            while time.monotonic() - sent < wait:
                b = self.t.read(1, timeout=0.2)
                if not b:
                    continue
                if b[0] == ~ecu & 0xFF:
                    return attempt, time.monotonic() - sent, bytes(junk), ecu
                junk += b
        return None

    def command(self, payload: bytes, retries=2):
        """Send a command list, check the echo, then send F0 to start streaming.

        The 1998 Maxima (seen 2026-11-14) sometimes answers a valid command with FE FE
        in place of the first echo pair, and sometimes echoes it correctly but answers
        F0 with FE and sends no frames. Both are retried after a stop.
        """
        want = expected_echo(payload)
        why = ""
        for n in range(retries + 1):
            self.t.write(payload)
            got = self.t.read(len(want), timeout=0.5)
            if got == want:
                self.t.write(bytes([GO]))
                first = self.t.read(1, timeout=0.5)
                if first == b"\xFF":
                    self._frame_started = True   # read_frame: FF already consumed
                    return
                why = f"F0 answered with {first.hex() or '(none)'}"
            else:
                why = f"bad echo {got.hex(' ') or '(none)'}, expected {want.hex(' ')}"
            self.t.note(f"command try {n + 1} failed: {why}")
            self.stop(timeout=0.5)
            self.t.drain(quiet=0.1)
        raise ConsultError(why)

    def read_frame(self, expected_len=None, timeout=1.0) -> bytes:
        """Read one FF <n> <data...> frame, parsing by length (data may contain FF)."""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if getattr(self, "_frame_started", False):
                self._frame_started = False
            else:
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
        tail = d[-5:]
        if len(d) >= 5 and all(0x30 <= b < 0x5B for b in tail):
            # 1998 Maxima: 32-byte frame ending in ASCII, e.g. "2L904" = 23710-2L904
            pn = "23710-" + tail.decode("ascii")
        elif len(d) >= 22:
            pn = f"{d[2]:02X}{d[3]:02X} 23710-{d[19]:X}{d[20]:02X}{d[21]:02X}"
        return d, pn

    def dtcs(self):
        d = self.one_shot(bytes([0xD1]))
        return d, [(d[i], d[i + 1]) for i in range(0, len(d) - 1, 2)]
