"""Strict, command-gated replay of existing TX/RX captures."""
from dataclasses import dataclass
import hashlib
import re


@dataclass(frozen=True)
class Record:
    time: float
    direction: str
    data: bytes
    line: int


def load_capture(path):
    raw = path.read_bytes()
    records = []
    for line_no, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        match = re.match(r"^\s*(\d+\.\d+)\s+(TX|RX)\s+(.+)$", line)
        if match:
            records.append(Record(float(match[1]), match[2],
                                  bytes.fromhex(match[3]), line_no))
    return records, hashlib.sha256(raw).hexdigest()


class Replay:
    """Require exact historical write calls, release only their subsequent RX.

    RX timestamps are relative to the triggering historical TX. Host scheduling
    may differ; this does not assert timing fidelity or prove old TX completion.
    Use a contiguous transaction slice beginning with TX and ending before the
    next transaction. Unread data and missing writes fail assert_complete().
    """
    def __init__(self, records):
        self.records = list(records)
        self.index = 0
        if not self.records or self.records[0].direction != "TX":
            raise ValueError("replay must begin with TX")
        if any(b.time < a.time for a, b in zip(self.records, self.records[1:])):
            raise ValueError("capture crosses a session timestamp reset")

    def __call__(self, data, wire):
        if self.index >= len(self.records):
            raise AssertionError(f"unexpected extra TX {data.hex()}")
        expected = self.records[self.index]
        if expected.direction != "TX" or data != expected.data:
            raise AssertionError(
                f"capture line {expected.line}: expected TX {expected.data.hex()}, "
                f"got {data.hex()}"
            )
        self.index += 1
        while self.index < len(self.records):
            record = self.records[self.index]
            if record.direction == "TX":
                break
            wire.feed(record.data, delay=record.time - expected.time)
            self.index += 1

    def assert_complete(self, wire):
        if self.index != len(self.records) or wire.pending or wire.events:
            raise AssertionError("capture not fully consumed")
