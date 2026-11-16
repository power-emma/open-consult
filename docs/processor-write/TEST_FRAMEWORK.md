# Offline protocol test framework

The framework runs production Python and C protocol code against the same
deterministic scenarios, replays an existing hardware transaction, and checks
production POSIX transport I/O over a pseudo-terminal. It never opens a physical
serial device. Python standard-library tools and a Linux C compiler are enough;
GTK and pyserial are not required for this Linux suite.

Passing simulation establishes behavior under modeled conditions. It cannot
guarantee hardware behavior: the ECU firmware, H8 scheduling, FTDI driver,
electrical link, and reset behavior must also match the model. In particular,
this framework does not yet validate the experimental memory-write primitive.

## Run it

From the repository root:

```sh
python tools/test_protocol.py
python tools/test_protocol.py --require-conformance --report /tmp/consult-tests.json
```

The first command is a development regression check. The second is the stricter
offline conformance gate: failures, errors, known gaps, unexpected successes, or
skips make it exit nonzero. The JSON report always marks `hardware_validated`
false. Passing that gate alone must never set it true.

The initial run contains 27 tests: 20 passing checks and seven expected failures
covering four production defects. They are the same three parser/deadline defects
in Python and C, plus a Python partial-write defect. No tests were skipped on
the initial Linux run. Production code has not been modified to fix them.

An expected failure becoming an unexpected success is deliberately a failing
test run. After fixing a defect, remove its `expectedFailure` decorator and
verify that its regression test passes normally. Do not remove the scenario or
reclassify unexplained failures to make the strict gate green.

## Components and fidelity

| Component | Executes | Establishes | Does not establish |
|---|---|---|---|
| Virtual clock/wire | Production protocol calls with scheduled fragments and faults | Reproducible parsing, timeouts, command counts | Actual USB/driver latency |
| Synthetic C9 peer | Independently implemented ordinary C9 responses from supplied memory | Request/echo/frame behavior for modeled local reads | ECU firmware execution, H8 forwarding, writes |
| Strict capture replay | Production code against exact recorded TX/RX bytes | Compatibility with one observed transaction | Validity of other commands or unseen timing |
| C bridge | Compiled `src/consult.c`, test serial callbacks | Real C protocol behavior without GTK | Production C serial transport or Windows backend |
| Linux PTY check | Production Python `Transport.read`/`write` | Real OS byte I/O with control-byte payloads | FTDI setup, electrical timing, modem-control ioctls |
| Contract tests | Hardening record validation and retry policy | Evidence/replay invariants in those helpers | Migration of production callers to those helpers |

The synthetic peer intentionally supports only preinitialized ordinary local C9
reads, one frame per F0, and stop. Unsupported commands, unknown memory, forwarded
addresses, and oversized requests fail rather than returning invented data. It
does not model continuously generated frames; schedule those explicitly in wire
scenarios. It does not derive its responses from production echo helpers.

The C bridge is built in a temporary directory with warnings treated as errors.
It links `src/consult.c` without `src/serial.c`. Python callbacks retain their
exceptions and raise them after C returns; a replay mismatch cannot silently
become a successful test. The bridge uses process globals and is intended for
sequential scenarios, not concurrent clients. Unsupported hosts skip C/PTY
checks, which makes the strict gate fail rather than imply platform coverage.

## Add a shared protocol scenario

Add a method to `ProtocolScenarios` in `tests/test_protocol_framework.py`. Both
language suites inherit it and use the same byte schedule and expected outcome.
For example:

```python
def test_delayed_empty_frame_then_result(self):
    wire = Wire(self.clock)
    wire.feed(bytes.fromhex("ff 00"), delay=0.01)
    wire.feed(bytes.fromhex("ff 01 ab"), delay=0.02)
    self.assertEqual(self.client(wire).read_frame(1), b"\xab")
```

`Wire.feed` accepts delay, fragment size, and fragment gap. `disconnect_at` injects
a link failure at virtual time. A bounded operation count catches spinning test
code. `Wire.trace` retains TX, RX, and notes for diagnostics. Calls to production
Python protocol time are patched to the virtual clock only within each test.
The C protocol's monotonic/sleep functions use that same clock through the bridge.

The simulated transport preserves the existing idle-timeout read semantics:
an absolute-deadline guarantee must be implemented in production, not supplied
by a more forgiving fake. The short-write test separately injects an OS return
count beneath the real Python transport to expose incomplete transmission.

## Add captured evidence

`harness.replay.load_capture` reads timestamped TX/RX records with source line
numbers and a SHA-256 of the whole original file. Select a contiguous transaction
beginning with TX; split sessions where timestamps reset. `Replay` requires exact
write bytes and call boundaries, releases subsequent RX relative to each TX,
and rejects extra commands. `assert_complete` also rejects unread responses.

The initial fixture is the first four-byte streamlist baseline in
`logs/2026-11-15_hidden-read.log`. Its whole-file SHA-256 is pinned in the test.
The observed result is four zero bytes; this fixture is an ordinary read and
must not be presented as evidence that the later plant succeeded. Historical
TX logs record intent, not confirmed OS acceptance or ECU execution.

For new fixtures, retain the original capture, pin its hash, identify the exact
transaction and expected result independently, and retain unsuccessful captures.
When a command sequence changes legitimately, add a separate scenario; do not
relax exact replay into unconditional canned replies. Replay timing is one
observed schedule, so retain synthetic adversarial schedules as well.

## Progress toward hardware confidence

1. Fix the four exposed defects and pass the strict offline gate. Add regressions
   for cleanup, uncertain F0 execution, and command retry policy as production
   code adopts the hardening contracts.
2. Expand captured fixtures to initialization, rejected commands, streaming stop,
   disconnect/recovery, and independently verified ordinary local/H8 reads.
3. For the write primitive, build the ROM-grounded execution model described in
   [HARDENING_PLAN.md](HARDENING_PLAN.md). First reproduce the confirmed overrun
   and explain the failed plant. Do not implement a fake that simply performs
   the desired write when it sees the desired payload.
4. Match model checkpoints against real target-memory observations and retain
   uncertainty about unobserved states. Until instruction execution or equivalent
   validated transitions exist, synthetic write success has no hardware claim.
5. On an isolated bench, run the same declared scenarios and capture real TX/RX,
   reset conditions, identity, timing, and independent target readback. Meet the
   repeatability gate in the plan, including failed/inconclusive trials.
6. Turn new bench captures into pinned replay regressions. Repeat hardware checks
   after firmware, cable/backend, or timing changes that invalidate assumptions.

The framework is a way to accumulate evidence and reject invalid assumptions.
Hardware readiness remains specific to the tested ECU revision, targets,
values, timings, and operating conditions.
