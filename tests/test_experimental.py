import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from consult.experimental import MutationUnverified, mutation_stream, require_research_ecu
from consult.protocol import ConsultError


class ExperimentalTests(unittest.TestCase):
    def client(self):
        client = Mock()
        client._mutation_attempted = False
        client.stop.return_value = (0xCF, b"")
        client.read_frame.return_value = b"\xaa"
        return client

    def test_successful_stream_is_single_attempt_and_latches_session(self):
        client = self.client()
        self.assertEqual(mutation_stream(client, b"\xc9\x10\x00", frames=1), [b"\xaa"])
        client.command.assert_called_once_with(b"\xc9\x10\x00", retries=0, mutation=True)
        with self.assertRaises(MutationUnverified):
            mutation_stream(client, b"\xc9\x10\x00", frames=1)
        self.assertEqual(client.command.call_count, 1)

    def test_failed_stream_retains_primary_and_cleanup_failure(self):
        client = self.client()
        primary = TimeoutError("lost frame")
        client.read_frame.side_effect = primary
        client.stop.return_value = (None, b"")
        with self.assertRaises(MutationUnverified) as caught:
            mutation_stream(client, b"\xc9\x10\x00", frames=1)
        self.assertIs(caught.exception.primary, primary)
        self.assertIsInstance(caught.exception.cleanup, ConsultError)
        client.stop.assert_called_once()

    def test_partial_command_failure_still_attempts_stop(self):
        client = self.client()
        client.command.side_effect = OSError("unplugged")
        with self.assertRaises(MutationUnverified):
            mutation_stream(client, b"\xc9\x10\x00", frames=1)
        client.stop.assert_called_once()
        client.read_frame.assert_not_called()

    def test_interrupt_stops_before_propagating(self):
        client = self.client()
        client.read_frame.side_effect = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            mutation_stream(client, b"\xc9\x10\x00", frames=1)
        client.stop.assert_called_once()

    def test_invalid_plan_does_no_io(self):
        for payload, frames in ((b"\xc9\x10", 1), (b"\xc9\x10\x00", 0),
                                (b"\x30", 1), (b"\xc9\x10\x00" * 21, 1)):
            with self.subTest(payload=payload, frames=frames):
                client = self.client()
                with self.assertRaises(ValueError):
                    mutation_stream(client, payload, frames=frames)
                client.command.assert_not_called()
                client.stop.assert_not_called()

    def test_unrecognized_firmware_fails_before_mutation(self):
        client = self.client()
        client.part_number.return_value = (b"", "23710-other")
        with self.assertRaises(ConsultError):
            require_research_ecu(client)
        client.command.assert_not_called()

    def test_plant_mismatch_cannot_be_returned_as_success(self):
        path = Path(__file__).resolve().parents[1] / "tools/c9_hidden_read.py"
        spec = importlib.util.spec_from_file_location("hidden_read_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        client = self.client()
        client.read_memory.return_value = b"\x00" * 4
        with patch("builtins.print"), self.assertRaises(ConsultError):
            module.run_verify(client, 0x5E25)
