"""Deterministic serial link and deliberately limited ECU peer.

Model responses are independent of consult.protocol helpers. Unsupported ECU
behavior fails closed; this is not an emulator of the processor-write primitive.
"""
import heapq
from dataclasses import dataclass


class Clock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        if seconds < 0:
            raise ValueError("negative delay")
        self.now += seconds


class Wire:
    """Transport-compatible virtual link, with idle-timeout read semantics.

    feed() schedules RX fragments. Write hooks implement a device or a strict
    capture replay. Disconnects are scheduled independently of RX data. The
    operation budget catches accidental infinite loops without wall-clock waits.
    """
    def __init__(self, clock, on_write=None, budget=10000):
        self.clock = clock
        self.on_write = on_write
        self.budget = budget
        self.events = []
        self.pending = bytearray()
        self.trace = []
        self.disconnect_at = float("inf")
        self._sequence = 0

    def _step(self):
        self.budget -= 1
        if self.budget < 0:
            raise AssertionError("virtual I/O operation budget exceeded")
        if self.clock.now >= self.disconnect_at:
            raise OSError("injected disconnect")

    def feed(self, data, *, delay=0, chunk_size=None, gap=0):
        if delay < 0 or gap < 0 or (chunk_size is not None and chunk_size <= 0):
            raise ValueError("invalid fragment schedule")
        size = chunk_size or max(1, len(data))
        for index, start in enumerate(range(0, len(data), size)):
            self._sequence += 1
            heapq.heappush(self.events, (
                self.clock.now + delay + index * gap,
                self._sequence, bytes(data[start:start + size]),
            ))

    def write(self, data):
        self._step()
        self.trace.append((self.clock.now, "TX", bytes(data)))
        if self.on_write:
            self.on_write(bytes(data), self)

    def read(self, n, timeout=0.5):
        if n < 0 or timeout < 0:
            raise ValueError("invalid read")
        self._step()
        out = bytearray()
        while len(out) < n:
            if self.pending:
                take = min(n - len(out), len(self.pending))
                out += self.pending[:take]
                del self.pending[:take]
                continue
            until = self.clock.now + timeout
            arrival = self.events[0][0] if self.events else float("inf")
            if self.disconnect_at <= min(until, arrival):
                self.clock.now = self.disconnect_at
                raise OSError("injected disconnect")
            if arrival > until:
                self.clock.now = until
                break
            at, _, data = heapq.heappop(self.events)
            self.clock.now = max(at, self.clock.now)
            self.pending += data
        if out:
            self.trace.append((self.clock.now, "RX", bytes(out)))
        return bytes(out)

    def drain(self, quiet=0.2, limit=3.0):
        end = self.clock.now + limit
        out = bytearray()
        while self.clock.now < end:
            chunk = self.read(256, timeout=min(quiet, end - self.clock.now))
            out += chunk
            if not chunk:
                break
        return bytes(out)

    def note(self, text):
        self.trace.append((self.clock.now, "NOTE", text))


@dataclass(frozen=True)
class Faults:
    chunk_size: int = 1
    gap: float = 0.001
    reply_delay: float = 0.002
    drop_frame: bool = False
    drop_stop_ack: bool = False
    reject_command: bool = False
    frame_override: bytes = None


class MemoryECU:
    """Synthetic ordinary C9 peer, initialized and idle at construction.

    Only known local addresses, C9 (1..8), F0, and STOP are supported. No hidden
    forwarding, initialization, active tests, continuous stream or RAM writes.
    """
    def __init__(self, memory, faults=None):
        self.memory = dict(memory)
        self.faults = faults or Faults()
        self.arguments = bytearray()
        self.addresses = []
        self.commands = 0
        self.executions = 0

    def _reply(self, wire, data):
        wire.feed(data, delay=self.faults.reply_delay,
                  chunk_size=self.faults.chunk_size, gap=self.faults.gap)

    def __call__(self, data, wire):
        echo = bytearray()
        for byte in data:
            if self.arguments:
                self.arguments.append(byte)
                echo.append(byte)
                if len(self.arguments) == 3:
                    self.addresses.append(int.from_bytes(self.arguments[1:], "big"))
                    self.arguments.clear()
                continue
            if byte == 0xC9:
                self.commands += 1
                self.arguments.append(byte)
                echo.append(0xFE if self.faults.reject_command else 0x36)
            elif byte == 0xF0:
                if not 1 <= len(self.addresses) <= 8:
                    raise AssertionError("model supports ordinary C9 only")
                if any(0x5D40 <= a <= 0x623F for a in self.addresses):
                    raise AssertionError("forwarded H8 access is outside this model")
                payload = bytes(self.memory[a] for a in self.addresses)
                self.executions += 1
                if not self.faults.drop_frame:
                    frame = self.faults.frame_override
                    self._reply(wire, frame if frame is not None else
                                bytes([0xFF, len(payload)]) + payload)
            elif byte == 0x30:
                self.addresses.clear()
                self.arguments.clear()
                if not self.faults.drop_stop_ack:
                    self._reply(wire, b"\xcf")
            else:
                raise AssertionError(f"unsupported model command {byte:02x}")
        if echo:
            self._reply(wire, bytes(echo))
