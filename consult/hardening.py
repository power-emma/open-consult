"""Proposed hardening contracts; not wired into the live Consult stack.

No serial ports are opened here. OS adapters must implement bounded calls before
these contracts can provide an end-to-end deadline guarantee.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol


class Completion(str, Enum):
    COMPLETE = "complete"
    DEADLINE = "deadline"
    CANCELLED = "cancelled"
    DISCONNECTED = "disconnected"
    OS_ERROR = "os_error"


class DrainStatus(str, Enum):
    # Accepting bytes into an OS buffer does not prove transmission or execution.
    UNKNOWN = "unknown"
    COMPLETE = "complete"
    FAILED = "failed"
    DEADLINE = "deadline"


@dataclass(frozen=True)
class WriteResult:
    requested: int
    accepted: int
    completion: Completion
    drain: DrainStatus = DrainStatus.UNKNOWN
    os_error: Optional[int] = None

    def __post_init__(self):
        if not 0 <= self.accepted <= self.requested:
            raise ValueError("accepted must be a prefix of the requested bytes")
        if self.completion == Completion.COMPLETE and self.accepted != self.requested:
            raise ValueError("complete requires every requested byte to be accepted")


class WriteFailure(IOError):
    def __init__(self, result: WriteResult):
        self.result = result
        super().__init__(
            f"{result.completion.value}: accepted {result.accepted}/{result.requested} bytes"
        )


class DeadlineTransport(Protocol):
    """Adapter boundary for future POSIX/Windows implementations.

    deadline is an absolute monotonic timestamp, shared across all stages.
    write_all raises WriteFailure with the accepted prefix on failure. A complete
    write does not imply a complete drain. read_exact raises on timeout and must
    retain any partial bytes in the error/evidence. Never pad missing bytes.
    """

    def write_all(self, data: bytes, *, deadline: float) -> WriteResult: ...

    def read_exact(self, count: int, *, deadline: float) -> bytes: ...


@dataclass(frozen=True)
class Frame:
    payload: bytes
    # Offsets in the raw RX byte stream, not host file character offsets.
    rx_start: int
    rx_end: int
    matches_expected_length: bool


class FrameReader(Protocol):
    """Read FF/length/payload, including a header consumed by command().

    Implementations must consume unexpected-length frames in full, preserve
    partial captures on failure, and recognize CF/FE only outside payloads.
    """

    def read_frame(
        self, *, expected_length: Optional[int], deadline: float
    ) -> Frame: ...


class OperationKind(str, Enum):
    OBSERVATION = "observation"
    ACTIVE_TEST = "active_test"
    MUTATION = "mutation"


class LinkState(str, Enum):
    IDLE = "idle"
    COMMAND = "command"
    STREAMING = "streaming"
    STOPPING = "stopping"
    UNCERTAIN = "uncertain"
    DISCONNECTED = "disconnected"


class MutationOutcome(str, Enum):
    NOT_ATTEMPTED = "not_attempted"
    UNVERIFIED = "unverified"
    UNKNOWN = "unknown"
    VERIFIED = "verified"
    MISMATCH = "mismatch"


@dataclass(frozen=True)
class RetryContext:
    kind: OperationKind
    # Caller must establish repeatability for the particular observation.
    repeatable: bool
    link: LinkState
    baseline_verified: bool
    retries_used: int
    max_retries: int

    def __post_init__(self):
        if self.retries_used < 0 or self.max_retries < 0:
            raise ValueError("retry counts must be nonnegative")


def may_retry(context: RetryContext) -> bool:
    """Conservative replay gate, not a recovery operation or retry loop.

    Mutation and active-test commands never replay automatically. Stop/re-init
    does not set baseline_verified; the observation procedure must establish it.
    """
    return (
        context.kind == OperationKind.OBSERVATION
        and context.repeatable
        and context.link == LinkState.IDLE
        and context.baseline_verified
        and context.retries_used < context.max_retries
    )


@dataclass(frozen=True)
class TransactionResult:
    transaction_id: str
    link: LinkState
    mutation: MutationOutcome
    stop_ack: Optional[int] = None
    primary_error: Optional[str] = None
    cleanup_error: Optional[str] = None


class AddressSpace(str, Enum):
    MAIN_BANK0 = "main_bank0"
    H8_FORWARDED_RAM = "h8_forwarded_ram"
    UNESTABLISHED = "unestablished"


class ByteValidity(str, Enum):
    UNKNOWN = "unknown"
    OBSERVED = "observed"
    SUSPECT = "suspect"
    VALIDATED = "validated"


@dataclass(frozen=True)
class MemoryObservation:
    """One measured byte; simulated values belong in separate model artifacts.

    request_address is the address sent on the wire. source_address is the
    effective CPU address, if established. Offsets identify the payload byte
    in the original RX stream; validation needs a separately recorded procedure.
    """

    run_id: str
    transaction_id: str
    request_address: int
    space: AddressSpace
    source_address: Optional[int]
    value: Optional[int]
    validity: ByteValidity
    raw_rx_offset: Optional[int]
    validation_reference: Optional[str] = None

    def __post_init__(self):
        for address in (self.request_address, self.source_address):
            if address is not None and not 0 <= address <= 0xFFFF:
                raise ValueError("expected a 16-bit address")
        if self.value is not None and not 0 <= self.value <= 255:
            raise ValueError("expected a byte")
        if self.raw_rx_offset is not None and self.raw_rx_offset < 0:
            raise ValueError("RX offset must be nonnegative")
        if self.validity != ByteValidity.UNKNOWN:
            if self.value is None or self.raw_rx_offset is None:
                raise ValueError("observations need a value and raw RX provenance")
        if self.validity == ByteValidity.VALIDATED:
            if not self.validation_reference or self.space == AddressSpace.UNESTABLISHED:
                raise ValueError("validated bytes need a procedure and established space")


class EvidenceSink(Protocol):
    """Future versioned sidecar writer; historical raw logs remain unchanged."""

    def record_write(self, transaction_id: str, result: WriteResult) -> None: ...

    def record_transaction(self, result: TransactionResult) -> None: ...

    def record_observation(self, observation: MemoryObservation) -> None: ...
