# Plan: reliable ECU memory access

Scope: harden the Consult transport, measurement, and experimental RAM-write
workflow on the owned 23710-2L904 ECU. This is a plan only; no hardware was
connected and no implementation was changed. It assumes “write access” means
the ECU RAM primitive in this repository.

## Starting point

[FINDINGS.md](FINDINGS.md) is the evidence baseline. Oversized forwarded C9
requests demonstrably corrupt RAM, but controlled downstream writes, streamlist
planting, and hidden-code reads remain unconfirmed. The immediate objective is
to distinguish transport failures, decoding artifacts, and incorrect firmware
model assumptions before trying to expand memory coverage.

## 1. Make host I/O dependable

Files: `consult/transport.py`, `src/serial.c`, and their headers/callers.

- Implement complete writes with a single monotonic deadline. Python currently
  ignores the return counts from `os.write` and pyserial `write`; handle partial
  writes, interruption, would-block, zero progress, and disconnect explicitly.
- Bound serial draining where the platform supports it and report failures;
  the C POSIX loop also needs a zero-progress exit and a total deadline.
- Distinguish intended TX bytes from bytes accepted by the OS. Existing logs
  record TX before the write completes; neither implies execution by the ECU.
- Use exclusive serial ownership where supported so the GUI and research CLI
  cannot interleave commands. Close handles on initialization/logging failure.

Acceptance: fault-injected short writes, blocked writes, and disconnects either
complete exactly once or return an explicit bounded failure; logs preserve the
accepted prefix and uncertainty.

## 2. Make framing and transactions trustworthy

Files: `consult/protocol.py`, `src/consult.c`.

- Share one absolute deadline across header and payload reads. Current reads can
  restart timeouts for each byte or stage and exceed the advertised timeout.
- On an unexpected frame length, consume the declared payload within protocol
  bounds before looking for the next header. Both implementations currently
  continue immediately, allowing payload bytes containing FF to become headers.
  For truncated frames, report desynchronization and require explicit recovery.
- Track command, streaming, stopping, and uncertain states, including the
  pre-consumed FF marker. Reset parser state deliberately during recovery.
- Keep bounded retries for operations known to be repeatable. Experimental
  mutations must use a single-attempt path: `Consult.command()` currently retries
  twice by default, including when F0 may already have executed. Lost replies
  must produce “outcome unknown,” followed by inspection rather than replay.
- Ensure stop/cleanup runs on exceptions and cancellation; preserve the original
  failure and separately record whether stop was acknowledged. A stop or re-init
  is not evidence that corrupted RAM was restored.

Acceptance: replay tests cover fragmented frames, embedded FF, unexpected
lengths, missing echoes, lost first frames, and stop failures. No mutating
transaction is silently resent.

## 3. Reconcile captures with the firmware model

Files: `tools/c9_overrun_test.py`, `tools/c9_actuator_test.py`,
`tools/c9_hidden_read.py`, and offline fixtures derived from preserved logs.

- Build an offline decoder that retains byte offsets and timestamps and reports
  malformed or incomplete captures rather than silently producing memory bytes.
- Consolidate duplicated simulation logic into one model with explicit initial
  RAM, byte order, store widths, F0 execution order, count/index aliasing, and
  reply-builder transitions. Separate ROM-supported behavior from assumptions
  about H8 latency and builder interleaving.
- Replay the confirmed overrun and failed actuator/plant sessions. Compare actual
  memory observations with model predictions, accounting for commands used to
  observe state and their side effects. Fix the first divergence before using
  modeled target counts as evidence.
- Remove unconditional success/safety wording from experimental tool output;
  label predictions, observed payloads, and verified target-memory changes
  separately. Preserve historical logs and recovered sessions unchanged.

Acceptance: explain the recorded failed plant, or document the precise remaining
unknown and prevent the tool from reporting it as a successful write.

## 4. Establish a measured hardware validation procedure

- Record ECU identity, host version, serial settings, initial state, complete
  commands, received frames, stop status, and reset history for each trial.
- Establish repeatable ordinary C9 reads first. Keep normal reads within their
  existing eight-address API limit; isolate oversized experimental requests.
- Choose a verified scratch location only after checking ROM references and
  observation side effects. Consult handler state is live state, not inherently
  harmless scratch. Use an isolated bench setup for mutation experiments.
- Capture baseline, one attempted mutation, independent target-memory readback,
  and surrounding state. A changed reply payload alone does not prove a write.
- Validate reset behavior rather than assuming a key cycle clears all state.
  After an unknown result, require a verified baseline before another mutation.
- Gate each subsequent stage on its predecessor: repeatable single-byte target
  change, repeatable multi-byte state, then streamlist/read-chain validation.
  Verification commands themselves must be checked for destroying the plant;
  the historical 0A sequence overwrites streamlist.

Acceptance: predeclare a repeatability target, initially at least 20 successful
independent baseline-to-result trials with all failures retained. Report observed
rate, timing variation, and reset conditions; this is an engineering gate, not a
statistical guarantee or proof of arbitrary write access.

## 5. Export memory with provenance

- Store raw captures, decoded bytes, per-byte validity, source address space,
  request layout, and decoder version together. Missing bytes remain unknown.
- Compare shifted request layouts and single-address samples to detect positional
  artifacts. Repetition/majority vote alone cannot remove systematic corruption.
- Treat H8 forwarded RAM, local main-CPU reads, and simulated hidden reads as
  distinct sources. Live RAM changes are not automatically decoding failures.
- Resume failed reads only after session recovery; never resume an uncertain
  write automatically. Publish coverage and verified bytes, not padded success.

Acceptance: known artifacts such as batch-8 positions 6–7 are flagged in offline
fixtures, and dumps cannot silently promote unknown bytes to validated data.

## Implementation order

Implement steps 1–2 with fake transports and POSIX pseudo-terminal tests, plus
Windows transport mocks and targeted Windows verification. Complete offline
capture/model reconciliation next. Hardware trials follow only after those
checks pass. Dump/export integration comes last. No general-purpose memory-write
API should be advertised until target-memory readback meets the validation gate.

## Concrete interfaces and behavior

Initial interface scaffolding and usage notes are in [CODE_STUBS.md](CODE_STUBS.md).
They are not connected to the live transport or ECU command path.
The [offline test framework](TEST_FRAMEWORK.md) now exercises the production
protocol implementations and records current conformance gaps.

These are proposed contracts, not APIs already present in the repository. Keep
the Python and C behavior equivalent, even where their error-handling styles
differ. Introduce these changes in small patches rather than rewriting both
stacks at once.

### Transport contract

Add a deadline-aware complete-write operation. Its result must preserve:

| Field | Meaning |
|---|---|
| Requested byte count | Size of the original buffer |
| Accepted byte count | Prefix accepted by the OS before completion or failure |
| Completion status | Complete, deadline expired, cancelled, disconnected, or OS error |
| Drain status | Completed, failed, timed out, or not established |
| OS error | Original platform error, without replacing it with cleanup errors |

In Python, return success only after the entire buffer has been accepted;
otherwise raise a structured exception carrying the partial result. In C,
replace the `void serial_write(...)` contract with an explicit status/result
and update every caller to check it before reading an echo or sending F0.

Algorithm:

1. Compute the deadline once at operation entry using a monotonic clock.
2. Attempt the unsent suffix; advance only by the actual accepted count.
3. On interruption, retry using the remaining time. On would-block, wait for
   writability within that same budget. Zero progress must not spin forever.
4. Stop immediately on disconnect, cancellation, or expiration. Preserve the
   accepted prefix and do not resend the whole buffer.
5. Treat drain as a separate transport condition. Inspect Windows write timeout
   configuration and synchronous `FlushFileBuffers`, as well as POSIX
   `tcdrain`: a deadline around a loop cannot bound a blocking driver call.
   Select a supported bounded mechanism or explicitly report that drain
   completion is unknown. Do not claim a hard bound that the platform cannot
   enforce.

At 9600 baud, 8N1 requires approximately 1.04 ms per transmitted byte; account
for command size when choosing budgets. Keep transport deadlines configurable
and use existing ECU timing as the initial compatibility baseline. Select final
defaults from measurements rather than making all timeouts shorter.

Retain existing idle-timeout reads for callers that need them, but introduce a
separate exact-read-until-deadline operation for protocol framing. This avoids
silently changing unrelated watch/GUI behavior.

Use OS-backed exclusive ownership where available. On Linux, evaluate
`TIOCEXCL` plus a cooperative lock for this project's tools, documenting that
already-open descriptors and privileged processes remain limitations. Windows
should retain exclusive handle sharing settings. Release ownership on every
constructor failure and close path.

### Parser contract

Represent parser progress explicitly as header search, length, and payload.
Use the same parser rules in frame reads, initialization, and stop processing;
all three currently consume frames and can otherwise disagree about boundaries.

- FF inside a declared payload is data. CF/FE inside that payload is also data
  and cannot acknowledge a stop.
- A complete unexpected-length frame is recorded and skipped as a unit. A
  truncated frame is retained as incomplete evidence and invalidates stream
  synchronization; do not scan its remainder as though a new header is certain.
- Accept zero-length frames as protocol frames, while requiring the caller's
  expected length before interpreting them as memory results.
- Keep the pre-consumed FF marker in parser state. A stop immediately following
  `command()` must account for that marker before parsing outstanding bytes.
  Currently Python `stop()` clears `_frame_started` before consuming them.
- A frame result carries raw offsets, observed length, payload, and whether it
  met the request contract. Never truncate or pad to satisfy an expected length.
- Validate address bounds, request counts, complete command arguments, and
  output buffer capacities before serial I/O. Keep the normal C9 limit at eight;
  make experimental oversized requests an explicit separate operation.

### Transaction and recovery contract

Keep transport synchronization and mutation outcome as separate state. For
example, a stop acknowledgment can restore an idle link while the mutation
outcome remains unknown and the RAM remains corrupted.

| Event | Link state | Mutation result | Permitted next step |
|---|---|---|---|
| Validation fails before transmission | Unchanged | Not attempted | Correct input |
| Partial command or bad echo | Recovery required | Not verified | Bounded cleanup, inspect/reset baseline |
| F0 submitted; first frame absent | Uncertain | Unknown | Stop, preserve evidence, inspect/reset baseline |
| Stream received; no target readback | Streaming | Unverified | Stop and perform validated observation |
| Stop acknowledgment received | Idle if parsing is synchronized | Unchanged | Observation or baseline check |
| Readback shows expected target and acceptable surrounding state | Depends on observation cleanup | Verified for this trial | Record result and restore baseline |
| USB disconnect or stop failure | Disconnected/uncertain | Preserve last established outcome | Reconnect and explicitly recover |

Track an execution interval rather than saying the host knows the ECU's exact
execution instant. Even a complete OS write of F0 is not an ECU acknowledgment.
Transaction identifiers are host-side evidence labels; the protocol has no
demonstrated exactly-once execution mechanism.

Introduce an operation policy with explicit categories: ordinary observation,
active test, and experimental mutation. Retry decisions must consider command
semantics and the last completed stage, rather than merely a timeout exception.
Reading handler state may itself alter handler state, so “observation” does not
imply that all retry side effects are irrelevant. Default unfamiliar mixed
commands to no automatic replay. Preserve the existing active-test cleanup
behavior while auditing its shared transport/parser dependencies.

Recovery procedure: retain partial bytes and the original error; attempt a
bounded stop only if the port remains usable; record the acknowledgment or its
absence; mark parser synchronization explicitly; perform a new identity/baseline
check before normal reuse. For a mutation trial, link re-init alone never
authorizes another attempt. Do not send additional probe commands simply to
make an uncertain state appear idle.

## Evidence format and offline reconciliation

Keep timestamped raw TX/RX logs compatible with existing readers where possible.
Add a versioned structured sidecar rather than silently redefining historical
`TX` records. A run manifest should contain:

- Run ID, UTC start, monotonic event times, source revision, dirty-tree status,
  tool arguments, OS/backend, port, baud, and configured timing.
- ECU identity and how it was obtained; reset actions reported by the operator
  versus reset state actually verified by reads.
- Transaction ID, operation category, requested/accepted byte counts, complete
  raw command, parser events, received frames, errors, and cleanup outcome.
- Source address space, requested addresses in order, frame-to-address mapping,
  before/after observations, expected result, and trial classification.
- Hashes of raw captures and derived artifacts, decoder/model version, and
  initial-state assumptions used for a simulation.

Historical replay must label unknown transmission completion as unknown; old TX
logs cannot retroactively establish how many bytes the OS accepted. Preserve
original timestamps and append offsets so every decoded byte can be traced to
its source capture.

For model reconciliation, create a table of observable checkpoints: baseline,
command echo, F0, first complete frame, subsequent frames, stop, and readback.
For each checkpoint record expected state, observed state, and uncertainty.
Instrument the shared model to emit ordered stores with old/new value, width,
destination, count/index before and after, and the ROM location supporting the
transition. Do not compare a post-overrun model snapshot directly with a
post-stream hardware snapshot without modeling the intervening execution.

Treat H8 response timing, stale-value availability, and mixed-builder execution
as independent hypotheses. Run alternative schedules offline and state which
observations distinguish them. Where a capture has no observation of internal
state, report multiple consistent explanations rather than choosing one by
assumption. Reproducing a simulation's own expected output is not validation.

## Test matrix

Use deterministic fake clocks/transports for deadlines and protocol tests;
reserve real elapsed-time assertions for integration tests with tolerances.
Feed identical framing fixtures to the Python and C parsers. Add a C protocol
test executable independent of GTK so core checks do not require the GUI stack.
The existing Makefile has no test target; add documented Python/C targets during
implementation.

| Area | Injected case | Required observation |
|---|---|---|
| Write completion | Multiple short successful writes | Exact buffer once, correct accepted counts |
| Write interruption | EINTR/EAGAIN between accepted prefixes | Remaining suffix only; original deadline retained |
| Write failure | Zero progress, unplug, OS error | Bounded failure with accepted prefix retained |
| Drain | Driver does not finish | Explicit bounded failure or documented unsupported bound |
| Deadlines | Bytes trickle just before idle timeout | Absolute operation budget still expires |
| Frame fragmentation | Header, length, payload split at every boundary | Same decoded result for every split |
| Frame boundaries | Unexpected length containing FF/CF/FE | Whole payload consumed, no false header/ack |
| Frame truncation | Missing length or partial payload | Incomplete evidence, recovery required |
| Pending header | Stop after command consumed FF | Remaining frame parsed before recognizing acknowledgment |
| Mutation execution | F0 accepted, response lost | Unknown result; no second mutation sent |
| Cleanup | Primary failure followed by stop failure | Both recorded; original failure remains primary |
| Ownership | Second cooperating process opens port | Refused before it sends command bytes |
| Request validation | Empty/oversized normal C9 or invalid address | Failure before any I/O |
| Historical replay | Overrun and failed plant captures | Evidence status agrees with FINDINGS.md |
| Dump quality | Known positional artifacts or missing bytes | Unknown/suspect bytes remain marked |

POSIX pseudo-terminal tests should exercise real short/fragmented I/O and port
closure. PTYs do not reproduce every modem-control ioctl or FTDI drain behavior;
isolate unsupported setup in the harness and retain a separate cable/backend
check. Windows mocks must be supplemented by Windows checks before claiming
cross-platform verification. Run C memory/bounds checks under available
sanitizers for malformed frame fixtures.

## Bench trial design and decision gates

Before mutation trials, prepare a written trial card with target identity,
initial-state checks, expected changed bytes, allowed collateral changes,
observation method, timing, cleanup, and reset verification. The operator must
be able to decide success/failure without changing criteria after seeing data.
If no appropriate scratch location or non-destructive observation is established,
remain at offline reconciliation; do not substitute an actuator flag as scratch.

Use three outcomes: verified success, verified mismatch, and inconclusive.
Keep inconclusive trials in the attempted-trial denominator. An observed write
with unexpected collateral state is a failed trial under this gate. Distinguish
stable reference bytes from naturally changing RAM when interpreting readback.

The initial gate is a predeclared batch of 20 independent attempts, each starting
from a verified baseline, with 20 verified successes and no unexplained collateral
change. Record failures even if a later batch passes; do not retry until there
are 20 successes and discard the unsuccessful attempts. Repeat a complete batch
after a separately verified reset and report both batches. This measures only
the tested target/value and conditions. Any broader destination/value claims
need their own declared coverage matrix and supporting trials.

Only after a controlled single-byte change is established should multi-byte
state be evaluated. Capture intermediate-state hazards and the possibility that
the ECU consumes a partially updated word. Do not assume frame counts observed
by the host equal exact internal write counts: bytes may be buffered and frames
may already be in flight when stop is transmitted. Report stop timing limits
and resulting state rather than promising an exact stop boundary.

Hidden-memory access has an additional gate: show that the observation path
actually dereferences the planted main-processor address, and that neither setup
nor verification replaces that address. A plausible code byte or agreement with
an H8 dump is insufficient to identify the address space. If that path cannot
be distinguished using available observations, leave the result unconfirmed.

## Delivery sequence and review artifacts

| Patch | Deliverable | Review evidence / exit criterion |
|---|---|---|
| 1 | Complete-write results, resource cleanup, ownership | Transport fault tests and audited callers |
| 2 | Deadline reads and consistent frame consumption in Python/C | Shared parser fixtures and PTY checks |
| 3 | Operation policies, uncertainty states, bounded cleanup | Lost-response trace proves no mutation replay |
| 4 | Structured evidence sidecars and offline decoder | Source offsets/hash linkage; original logs unchanged |
| 5 | Shared firmware model and divergence report | Confirmed overrun explained; failed plant explained or unresolved assumptions identified |
| 6 | Bench procedure and measured trial report | Declared target/batch results, all failures, verified resets |
| 7 | Provenance-aware memory exports and documentation | Artifact detection fixtures and per-byte validity survive export/import |

Patches 1–5 can be prepared and reviewed without a vehicle or ECU connection.
Patch 6 depends on bench hardware and an established observation procedure;
it must not be reported complete on simulated evidence. Export schema work can
start earlier, but write-assisted memory coverage remains behind the hardware
gate. Update README/WRITE_PRIMITIVE capability wording only to the level
supported by the resulting evidence.

Completion means reliable bounded host behavior, reproducible decoding,
explicit uncertainty, and demonstrated results for declared targets. It does
not require turning the constrained primitive into arbitrary RAM access, ROM
flashing, or code execution. If the firmware mechanism cannot meet the gate,
the deliverable is a trustworthy failure report and reliable ordinary reads,
with the experimental write capability still marked unconfirmed.
