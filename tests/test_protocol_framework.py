"""Shared scenarios exercise production Python and C protocol code offline."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from consult.protocol import Consult
from harness.c_client import CClient, build_bridge
from harness.replay import Replay, load_capture
from harness.wire import Clock, Faults, MemoryECU, Wire

ROOT = Path(__file__).resolve().parents[1]


class ProtocolScenarios:
    def setUp(self):
        self.clock = Clock()
        self.clock_patch = patch("consult.protocol.time", self.clock)
        self.clock_patch.start()
        self.addCleanup(self.clock_patch.stop)

    def client(self, wire):
        return Consult(wire)

    def test_memory_bytes_containing_control_values(self):
        for chunk_size in (1, 2, 64):
            with self.subTest(chunk_size=chunk_size):
                peer = MemoryECU({0x1000: 0xFF, 0x1001: 0xCF, 0x1002: 0xFE},
                                 Faults(chunk_size=chunk_size))
                wire = Wire(self.clock, peer)
                self.assertEqual(self.client(wire).read_memory([0x1000, 0x1001, 0x1002]),
                                 b"\xff\xcf\xfe")
                self.assertEqual(peer.executions, 1)

    def test_all_frame_split_boundaries(self):
        frame = b"\xff\x03\xff\xcf\xfe"
        for split in range(1, len(frame)):
            with self.subTest(split=split):
                wire = Wire(self.clock)
                wire.feed(frame[:split], delay=0.01)
                wire.feed(frame[split:], delay=0.03)
                self.assertEqual(self.client(wire).read_frame(3), b"\xff\xcf\xfe")

    def test_truncated_payload_is_not_a_memory_result(self):
        wire = Wire(self.clock)
        wire.feed(b"\xff\x03\xaa")
        with self.assertRaises(TimeoutError):
            self.client(wire).read_frame(3)

    def test_missing_stop_ack_is_reported(self):
        peer = MemoryECU({}, Faults(drop_stop_ack=True))
        wire = Wire(self.clock, peer)
        self.assertIsNone(self.client(wire).stop(timeout=0.5)[0])

    def test_single_attempt_does_not_reexecute_after_lost_reply(self):
        peer = MemoryECU({0x1000: 0x42}, Faults(drop_frame=True))
        wire = Wire(self.clock, peer)
        with self.assertRaises(IOError):
            self.client(wire).command(b"\xc9\x10\x00", retries=0)
        self.assertEqual(peer.executions, 1)

    def test_oversized_list_cannot_inherit_default_retries(self):
        executions = []
        payload = b"\xc9\x5d\x40" * 9

        def peer(data, wire):
            if data == payload:
                wire.feed(b"\x36\x5d\x40" * 9)
            elif data == b"\xf0":
                executions.append(data)  # executed, but the reply is lost
            elif data == b"\x30":
                wire.feed(b"\xcf")
            else:
                raise AssertionError("unexpected command")

        wire = Wire(self.clock, peer)
        with self.assertRaises(IOError):
            self.client(wire).command(payload, retries=2)
        self.assertEqual(len(executions), 1)

    def test_truncated_payload_prevents_false_stop_ack(self):
        wire = Wire(self.clock)
        wire.feed(b"\xff\x03\xaa")
        client = self.client(wire)
        with self.assertRaises(TimeoutError):
            client.read_frame(3, timeout=0.1)
        wire.feed(b"\xcf")
        self.assertIsNone(client.stop()[0])

    def test_historical_memory_read(self):
        path = ROOT / "logs/2026-11-15_hidden-read.log"
        records, digest = load_capture(path)
        # First streamlist baseline: exact TX/RX, through its STOP acknowledgment.
        start = next(i for i, r in enumerate(records)
                     if r.direction == "TX" and r.data == bytes.fromhex(
                         "c9 07 a0 c9 07 a1 c9 07 a2 c9 07 a3"))
        end = next(i for i in range(start + 1, len(records))
                   if records[i].direction == "TX" and len(records[i].data) > 20)
        replay = Replay(records[start:end])
        wire = Wire(self.clock, replay)
        self.assertEqual(digest,
                         "aa5aee45dd0f8e7a1f4eb0513db0727d9f266aab30f5804dbb530ff045e6877e")
        self.assertEqual(self.client(wire).read_memory([0x7A0, 0x7A1, 0x7A2, 0x7A3]),
                         b"\x00" * 4)
        replay.assert_complete(wire)

    def test_regression_unexpected_frame_payload_cannot_supply_false_header(self):
        wire = Wire(self.clock)
        wire.feed(bytes.fromhex("ff 03 ff 01 ee ff 01 ab"))
        self.assertEqual(self.client(wire).read_frame(1), b"\xab")

    def test_regression_stop_accounts_for_preconsumed_header(self):
        peer = MemoryECU({0x1000: 0xCF})
        wire = Wire(self.clock, peer)
        client = self.client(wire)
        client.command(b"\xc9\x10\x00", retries=0)
        # The real ack is FE. CF belongs to the still-pending frame payload.
        peer.faults = Faults(drop_stop_ack=True)
        wire.feed(b"\xfe", delay=0.02)
        self.assertEqual(client.stop()[0], 0xFE)

    def test_regression_absolute_frame_deadline(self):
        wire = Wire(self.clock)
        wire.feed(b"\xff", delay=0.09)
        wire.feed(b"\x01", delay=0.18)
        wire.feed(b"\xab", delay=0.27)
        start = self.clock.now
        try:
            self.client(wire).read_frame(1, timeout=0.1)
        except TimeoutError:
            pass
        self.assertLessEqual(self.clock.now - start, 0.100001)


class PythonProtocolTests(ProtocolScenarios, unittest.TestCase):
    pass


@unittest.skipUnless(sys.platform.startswith("linux") and shutil.which("cc"),
                     "C bridge requires Linux and cc; not hardware validation")
class CProtocolTests(ProtocolScenarios, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="consult-test-")
        cls.addClassCleanup(cls.directory.cleanup)
        cls.library = build_bridge(cls.directory.name)

    def client(self, wire):
        return CClient(self.library, wire)


class HarnessIntegrityTests(unittest.TestCase):
    def test_replay_rejects_extra_and_changed_writes(self):
        from harness.replay import Record
        replay = Replay([Record(0, "TX", b"\x30", 1),
                         Record(.01, "RX", b"\xcf", 2)])
        wire = Wire(Clock(), replay)
        with self.assertRaises(AssertionError):
            wire.write(b"\xf0")
        wire.write(b"\x30")
        with self.assertRaises(AssertionError):
            replay.assert_complete(wire)
        self.assertEqual(wire.read(1), b"\xcf")
        replay.assert_complete(wire)
        with self.assertRaises(AssertionError):
            wire.write(b"\x30")

    def test_unmodeled_memory_does_not_become_zero(self):
        peer = MemoryECU({})
        wire = Wire(Clock(), peer)
        wire.write(b"\xc9\x10\x00")
        with self.assertRaises(KeyError):
            wire.write(b"\xf0")

    def test_disconnect_occurs_without_wall_clock_wait(self):
        wire = Wire(Clock())
        wire.disconnect_at = 0.05
        with self.assertRaises(OSError):
            wire.read(1, timeout=2)
        self.assertEqual(wire.clock.now, 0.05)


if __name__ == "__main__":
    unittest.main()
