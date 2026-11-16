"""Offline checks for evidence and replay invariants; no serial access."""
from dataclasses import replace
import unittest

from consult.hardening import (
    AddressSpace, ByteValidity, Completion, DrainStatus, LinkState,
    MemoryObservation, OperationKind, RetryContext, WriteFailure, WriteResult,
    may_retry,
)


class HardeningContractsTest(unittest.TestCase):
    def test_mutation_cannot_inherit_observation_retry_permission(self):
        recovered_read = RetryContext(
            OperationKind.OBSERVATION, True, LinkState.IDLE, True, 0, 2
        )
        self.assertTrue(may_retry(recovered_read))
        for kind in (OperationKind.MUTATION, OperationKind.ACTIVE_TEST):
            self.assertFalse(may_retry(replace(recovered_read, kind=kind)))
        self.assertFalse(may_retry(replace(recovered_read, link=LinkState.UNCERTAIN)))
        self.assertFalse(may_retry(replace(recovered_read, baseline_verified=False)))

    def test_failed_write_retains_partial_progress_without_claiming_drain(self):
        result = WriteResult(60, 17, Completion.DEADLINE)
        error = WriteFailure(result)
        self.assertEqual(error.result.accepted, 17)
        self.assertEqual(error.result.drain, DrainStatus.UNKNOWN)
        with self.assertRaises(ValueError):
            replace(result, completion=Completion.COMPLETE)

    def test_missing_capture_cannot_be_promoted_to_observed_data(self):
        unknown = MemoryObservation(
            "run-1", "tx-1", 0x1000, AddressSpace.UNESTABLISHED,
            None, None, ByteValidity.UNKNOWN, None,
        )
        with self.assertRaises(ValueError):
            replace(unknown, validity=ByteValidity.OBSERVED)
        # Zero is a real byte, not the sentinel for missing data.
        observed = replace(
            unknown, value=0, raw_rx_offset=0, validity=ByteValidity.OBSERVED
        )
        self.assertEqual(observed.value, 0)

    def test_validation_requires_procedure_and_established_address_space(self):
        observed = MemoryObservation(
            "run-1", "tx-1", 0x1000, AddressSpace.UNESTABLISHED,
            None, 0xAB, ByteValidity.OBSERVED, 12,
        )
        with self.assertRaises(ValueError):
            replace(observed, validity=ByteValidity.VALIDATED)
        with self.assertRaises(ValueError):
            replace(observed, validity=ByteValidity.VALIDATED,
                    validation_reference="trial-1")


if __name__ == "__main__":
    unittest.main()
