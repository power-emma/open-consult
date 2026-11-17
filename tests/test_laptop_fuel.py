"""Map math and controller transitions, using a deterministic synthetic peer."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from consult.fuel_map import FuelMap
from consult.protocol import ConsultError
import laptop_fuel as laptop


class FuelMapTests(unittest.TestCase):
    def test_bilinear_interpolation_and_boundary_clamping(self):
        grid = FuelMap({'rpm_axis': [1000, 3000], 'load_code_axis': [0, 1000],
                        'fuel_percent': [[90, 100], [110, 120]]})
        self.assertEqual(grid.lookup(2000, 500), 105)
        self.assertEqual(grid.lookup(-100, -1), 90)
        self.assertEqual(grid.lookup(9000, 65535), 120)
        self.assertEqual(grid.lookup(3000, 500), 110)

    def test_null_means_stock_not_fixed_100(self):
        grid = FuelMap({'rpm_axis': [1000, 2000], 'load_code_axis': [0, 100],
                        'fuel_percent': [[103, None], [103, None]]})
        self.assertEqual(grid.lookup(1000, 50), 103)
        self.assertIsNone(grid.lookup(1500, 50))
        self.assertIsNone(FuelMap.constant(None).lookup(1000, 0))
        self.assertEqual(FuelMap.constant(100).lookup(1000, 0), 100)

    def test_reject_bad_map_shapes_limits_and_nonfinite_values(self):
        for document in ([], {}, {'rpm_axis': [1, 1], 'load_code_axis': [0, 1],
                                  'fuel_percent': [[100, 100], [100, 100]]}):
            with self.subTest(document=document), self.assertRaises(ValueError):
                FuelMap(document)
        for value in (74, 126, float('nan'), float('inf'), True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                FuelMap.constant(value)
        with self.assertRaises(ValueError):
            FuelMap.constant(100).lookup(float('nan'), 0)


class Peer:
    """Behavioral peer for controller logic, not an emulator of ECU firmware."""
    def __init__(self):
        self.now = 0.0
        self.current = None
        self.commands = []
        self.stops = 0
        self.released = False
        self.rejected = False
        self.never_apply = False
        self.frames_since_command = 0
        self.settle_frames = 0
        self.bad_stop = False
        self.engine_stopped = False

    def command(self, command, **kwargs):
        self.commands.append(command)
        if self.rejected:
            raise ConsultError('injected rejection')
        self.current = command[2] if command[0] == 0x0A else None
        self.frames_since_command = 0
        self.released = self.current is None

    def stop(self, **kwargs):
        self.stops += 1
        self.current = None
        self.released = True
        return (None if self.bad_stop else 0xCF), b''

    def read_frame(self, **kwargs):
        self.now += 0.05
        self.frames_since_command += 1
        desired = 100 if self.current is None else self.current
        applied = 100 if self.never_apply or self.frames_since_command <= self.settle_frames else desired
        flags = 0 if self.current is None else 2
        return bytes([0, 0 if self.engine_stopped else 80, 0, 100, applied, applied,
                      0, 250, 0, 250, flags, desired, 0])

    def read_checked(self, client, addresses):
        self.now += 0.005
        if addresses == [0x07B7]:
            return bytes([0 if self.released else 2])
        return bytes([0, 0 if self.engine_stopped else 80, 0, 100])


class LaptopControllerTests(unittest.TestCase):
    def run_peer(self, peer, lookup, duration=0.8):
        report, samples, events = {}, [], []
        with patch.object(laptop, 'read_checked', side_effect=peer.read_checked):
            result = laptop.run_controller(peer, lookup, duration, report,
                lambda sample, state: samples.append(sample),
                lambda event, state: events.append(dict(event)),
                clock=lambda: peer.now, settle_timeout=0.3)
        return result, report, samples

    def test_unchanged_percent_keeps_one_stream_and_releases(self):
        peer = Peer()
        result, report, samples = self.run_peer(peer, lambda rpm, load: 103)
        self.assertTrue(result)
        self.assertEqual(len(peer.commands), 1)
        self.assertTrue(report['requests'][0]['verified'])
        self.assertTrue(report['override_released'])
        self.assertGreater(len(samples), 3)

    def test_map_change_stops_and_applies_new_percentage(self):
        peer = Peer()
        def lookup(rpm, load):
            return 100 if peer.now < 0.3 else 103
        result, report, samples = self.run_peer(peer, lookup)
        self.assertTrue(result)
        self.assertEqual([r['percent'] for r in report['requests']], [100, 103])
        self.assertIn('stop_to_request_ack_seconds', report['requests'][1])
        self.assertEqual(peer.stops, 2)  # transition + final

    def test_stock_to_override_and_back_uses_native_and_read_only_commands(self):
        peer = Peer()
        def lookup(rpm, load):
            return 103 if 0.25 <= peer.now < 0.55 else None
        result, report, _ = self.run_peer(peer, lookup, 1)
        self.assertTrue(result)
        self.assertEqual([r['percent'] for r in report['requests']], [None, 103, None])
        self.assertEqual([command[0] for command in peer.commands], [0xC9, 0x0A, 0xC9])

    def test_parameter_echo_without_applied_banks_fails_and_stops(self):
        peer = Peer()
        peer.never_apply = True
        with self.assertRaises(ConsultError):
            self.run_peer(peer, lambda rpm, load: 103)
        self.assertTrue(peer.released)
        self.assertEqual(len(peer.commands), 1)

    def test_rejection_does_not_retry(self):
        peer = Peer()
        peer.rejected = True
        with self.assertRaises(ConsultError):
            self.run_peer(peer, lambda rpm, load: 103)
        self.assertEqual(len(peer.commands), 1)
        self.assertTrue(peer.released)

    def test_missing_final_stop_ack_is_not_a_completed_run(self):
        peer = Peer()
        peer.bad_stop = True
        with self.assertRaises(ConsultError):
            self.run_peer(peer, lambda rpm, load: 103)

    def test_engine_off_prevents_first_request(self):
        peer = Peer()
        peer.engine_stopped = True
        with self.assertRaises(ConsultError):
            self.run_peer(peer, lambda rpm, load: 103)
        self.assertEqual(peer.commands, [])

    def test_early_settling_frames_do_not_fail_before_timeout(self):
        peer = Peer()
        peer.settle_frames = 2
        result, report, _ = self.run_peer(peer, lambda rpm, load: 103)
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
