"""Single-attempt streaming for experimental mutations, not a memory-write API."""
from .protocol import ConsultError, NARGS, expected_echo


class MutationUnverified(ConsultError):
    def __init__(self, primary=None, cleanup=None):
        self.primary = primary
        self.cleanup = cleanup
        super().__init__(f"mutation unverified; primary={primary!r}; cleanup={cleanup!r}")


def require_research_ecu(c):
    """This payload/model is specific to one recorded firmware identity."""
    _, identity = c.part_number()
    if identity != "23710-2L904":
        raise ConsultError(f"research payload unsupported for ECU {identity!r}")


def mutation_stream(c, payload, *, frames, expected_len=None):
    """Validate first, execute once, and require acknowledged cleanup.

    Received frames are evidence only. They do not verify target RAM, and the
    requested frame count does not imply an exact internal write count. Failure
    blocks follow-up phases by raising, retaining both primary/cleanup errors.
    """
    if not isinstance(frames, int) or isinstance(frames, bool) or not 1 <= frames <= 1000:
        raise ValueError("frames must be an integer in 1..1000")
    if expected_len is not None and not 0 <= expected_len <= 255:
        raise ValueError("invalid expected frame length")
    if not payload or len(payload) > 64:
        raise ValueError("experimental command must contain 1..64 bytes")
    expected_echo(payload)  # Reject incomplete arguments before I/O.
    i, arguments = 0, 0
    while i < len(payload):
        cmd = payload[i]
        if cmd not in (0xC9, 0x0A):
            raise ValueError("experimental stream accepts C9/0A lists only")
        arguments += NARGS[cmd]
        i += 1 + NARGS[cmd]
    if arguments > 40:
        raise ValueError("experimental command exceeds the 40-byte argument buffer")
    if getattr(c, "_mutation_attempted", False):
        raise MutationUnverified("session already attempted a mutation; fresh verified baseline required")
    # Re-init must not silently clear this latch. A new trial requires an
    # explicitly prepared session; this is not a substitute for reset readback.
    c._mutation_attempted = True

    received = []
    primary = cleanup = None
    try:
        c.command(payload, retries=0, mutation=True)
        for _ in range(frames):
            received.append(c.read_frame(expected_len=expected_len, timeout=1.0))
    except BaseException as error:
        primary = error
    finally:
        try:
            ack, _ = c.stop(timeout=0.5)
            if ack is None:
                cleanup = ConsultError("stop acknowledgment missing; baseline recovery required")
        except BaseException as error:
            cleanup = error
    if primary is not None or cleanup is not None:
        c.t.note(f"mutation unverified: primary={primary!r}; cleanup={cleanup!r}")
        # Preserve interruption semantics after the cleanup attempt.
        if isinstance(primary, (KeyboardInterrupt, SystemExit)):
            raise primary
        raise MutationUnverified(primary, cleanup) from primary
    c.t.note(f"single mutation attempt; {len(received)} frames; stop acknowledged; RAM unverified")
    return received
