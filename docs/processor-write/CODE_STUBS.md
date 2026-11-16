# Hardening code stubs

These files scaffold the [hardening plan](HARDENING_PLAN.md). They do not open a
port, send commands, improve the existing transport, or establish a working ECU
memory-write capability.

| File | What is provided | What remains |
|---|---|---|
| `consult/hardening.py` | Validated result/evidence records, conservative retry gate, adapter/parser/sink protocols | OS adapters, parser, transaction controller, sidecar persistence |
| `src/consult_hardening.h` | C result/state types and proposed function declarations | Definitions, caller migration, C tests |
| `tests/test_hardening_contracts.py` | Offline checks against accidental replay and evidence promotion | Fault-injected I/O, parser/recovery fixtures, platform tests |

Python protocols describe required methods; they are not usable serial adapter
implementations. The C functions are declarations only and cannot be called in a
linked executable until definitions are added. Neither live stack imports or
includes these stubs.

## Example: recording an incomplete host write

```python
from consult.hardening import Completion, WriteFailure, WriteResult

# An adapter would produce this from actual OS write return counts.
result = WriteResult(requested=60, accepted=17, completion=Completion.DEADLINE)
error = WriteFailure(result)
# Preserve error.result in evidence. Do not resend the original 60-byte command.
# Accepted bytes do not establish how much the ECU consumed or executed.
```

## Example: deciding whether an observation may be retried

```python
from consult.hardening import LinkState, OperationKind, RetryContext, may_retry

policy = RetryContext(
    kind=OperationKind.OBSERVATION,
    repeatable=True,                 # established for this particular command
    link=LinkState.IDLE,              # established by protocol recovery
    baseline_verified=True,          # established separately by observation
    retries_used=0,
    max_retries=2,
)
assert may_retry(policy)
# Changing kind to MUTATION or ACTIVE_TEST always denies automatic replay.
```

The gate does not perform recovery or verify a baseline. A future controller must
supply those facts; setting booleans is not proof. Likewise, constructing a
`VALIDATED` memory record does not validate the measurement: the referenced
procedure and raw capture must support that classification.

## Suggested next implementation

1. Implement/test a bounded POSIX adapter behind `DeadlineTransport`, retaining
   the accepted prefix on failure. Audit driver draining before claiming bounds.
2. Add a fake-clock frame reader and verify fragmentation, unexpected lengths,
   and pre-consumed headers before connecting it to production calls.
3. Introduce a controller that owns link transitions, F0 uncertainty, cleanup,
   and baseline recovery. Keep transaction outcome separate from link recovery.
4. Implement `EvidenceSink` using a versioned sidecar and stable run/transaction
   IDs. Preserve existing raw logs and reference byte offsets explicitly.
5. Port validated behavior to C and migrate callers in reviewable patches.

The current normal `Consult.command()` retry behavior remains active until that
migration; importing these types alone does not make experimental calls safe to
retry.

Run the offline contract checks from the repository root:

```sh
python -m unittest discover -s tests -p 'test_hardening_contracts.py' -v
```
