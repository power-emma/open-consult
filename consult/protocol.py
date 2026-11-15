"""Consult-I protocol layer (CONSULT_PROTOCOL.md §3–4).

Read-side commands plus active tests (0A, CONSULT_PROTOCOL.md §7). DTC clear (C1) is
still left out on purpose.
"""
import time

ENGINE = 0xEF
ENGINE_ALT = 0xED               # the 1998 Maxima's engine ECU answers ED (reply 12), not EF
ENGINE_IDS = (ENGINE_ALT, ENGINE)
STOP = 0x30
GO = 0xF0
STOP_ACKS = (0xCF, 0xFE)        # both seen on the A32 (CONSULT_PROTOCOL.md §3, rule 7)
ACTIVE = 0x0A

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
        """Send 30 and read until a stop ack. Returns (ack byte or None, bytes before it).

        Whole frames are skipped by length, so a data byte that happens to be CF or FE
        isn't taken for the ack. Only whole frames come before the ack (checklist 1.5).
        """
        self.t.write(bytes([STOP]))
        self._frame_started = False
        before = bytearray()
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            b = self.t.read(1, timeout=0.3)
            if not b:
                continue
            before += b
            if b[0] == 0xFF:
                n = self.t.read(1, timeout=0.3)
                before += n
                if n:
                    before += self.t.read(n[0], timeout=0.3)
                continue
            if b[0] in STOP_ACKS:
                return b[0], bytes(before[:-1])
        return None, bytes(before)

    def init(self, ecu=ENGINE_IDS, tries=5, wait=2.0, pre_stop=True, gaps=(0.28, 0.07)):
        """Send FF FF <ecu> until ~ecu (10 for EF, 12 for ED) comes back.

        `ecu` is one ID or a sequence of IDs tried in turn on each attempt. The
        default tries ED first and then EF: the 1998 Maxima answers ED. After a
        wrong-ID init the ECU ignores everything, including 30, until it gets a
        correct init.

        `gaps` are the pauses after the first and second FF. ECUTalk 1.5.0 sends the
        three bytes separately with Sleep(Delay1=280 ms) and Sleep(Delay2=70 ms) in
        between (decompiled from ECUTalk). Pass gaps=None to send them back to back.

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
                if b[0] == 0xFF:
                    # A frame from a unit still streaming (the BCM keeps streaming
                    # after key-off, 2026-11-15): skip it by length, or its bytes
                    # can pass for the reply (FF 12 looked like an ED init).
                    n = self.t.read(1, timeout=0.2)
                    junk += b + n
                    if n:
                        junk += self.t.read(n[0], timeout=0.2)
                    continue
                if b[0] == ~ecu & 0xFF:
                    self.ecu = ecu
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
            got = self._send(payload, want)
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

    @property
    def paced(self):
        # The BCM (DA) answers FE to a command list sent in one burst, but accepts the
        # same bytes sent one at a time, each after its echo (2026-11-14).
        return getattr(self, "ecu", ENGINE) not in ENGINE_IDS

    def _send(self, payload, want):
        if not self.paced:
            self.t.write(payload)
            return self.t.read(len(want), timeout=0.5)
        got = bytearray()
        for i, b in enumerate(payload):
            self.t.write(bytes([b]))
            e = self.t.read(1, timeout=0.3)
            got += e
            if e != want[i:i + 1]:
                break
        return bytes(got)

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
        engine = getattr(self, "ecu", ENGINE) in ENGINE_IDS
        if len(d) >= 5 and all(0x30 <= b < 0x5B for b in tail):
            # 1998 Maxima: frame ending in ASCII, e.g. "2L904" = 23710-2L904. Only the
            # engine ECU is known to be 23710-; other units get the bare suffix.
            pn = ("23710-" if engine else "?-") + tail.decode("ascii")
        elif engine and len(d) >= 22:
            pn = f"{d[2]:02X}{d[3]:02X} 23710-{d[19]:X}{d[20]:02X}{d[21]:02X}"
        return d, pn

    def read_memory(self, addrs):
        """C9: one byte from each address (1..8 per request, CONSULT_PROTOCOL.md §4)."""
        if not 1 <= len(addrs) <= 8:
            raise ValueError("C9 takes 1..8 addresses per request")
        payload = b"".join(bytes([0xC9, a >> 8, a & 0xFF]) for a in addrs)
        return self.one_shot(payload, expected_len=len(addrs))

    def dtcs(self):
        d = self.one_shot(bytes([0xD1]))
        return d, [(d[i], d[i + 1]) for i in range(0, len(d) - 1, 2)]

    def active_test(self, test, value, hold=5.0, on_rx=None):
        """Send 0A <test> <value> F0, hold for `hold` seconds, then stop (30).

        No retries: a bad echo stops and raises. The stop is sent whatever happens,
        including Ctrl-C, and resent up to 3 times if it isn't acknowledged.
        `on_rx(bytes)` is called with whatever the ECU sends during the hold.

        Returns (bytes received during the hold, stop ack or None).
        """
        payload = bytes([ACTIVE, test, value])
        want = expected_echo(payload)
        got = bytearray()
        try:
            echo = self._send(payload, want)    # paced for the BCM
            if echo != want:
                raise ConsultError(f"bad echo {echo.hex(' ') or '(none)'}, expected {want.hex(' ')}")
            self.t.write(bytes([GO]))
            self.t.note(f"active test {test:02X}={value:02X} on, holding {hold:.1f} s")
            end = time.monotonic() + hold
            while time.monotonic() < end:
                chunk = self.t.read(64, timeout=0.2)
                if chunk:
                    got += chunk
                    if on_rx:
                        on_rx(chunk)
        finally:
            ack = None
            for _ in range(3):
                ack, _ = self.stop()
                if ack is not None:
                    break
            self.t.note(f"active test {test:02X} stopped, ack {ack if ack is None else f'{ack:02X}'}")
        return bytes(got), ack
