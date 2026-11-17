# Direct request-builder RAM write test

The new path writes at `$54A0` inside `c9_find_hidden`, rather than relying on
the later `$9B5E` reply-placement write. Hardware testing at `$0817` has now
verified all 256 chosen byte values; other addresses require separate validation.
The saved [sweep report](../logs/2026-11-16_202021_963725_direct-sweep.json)
contains 256 changed baselines, matching target/companion bytes in both later
readbacks, and acknowledged mutation stops. Recorded elapsed time is 47.6981 s.

## Test script

From the repository root, preview without opening a serial port:

```sh
python3 tools/c9_direct_test.py --target 0817 --value 42
```

With the key on and engine off, execute one trial:

```sh
python3 tools/c9_direct_test.py --target 0817 --value 42 --run --dev /dev/ttyUSB0
```

On Windows, substitute `--dev COM4` (or the actual cable port). The script uses
the existing Consult transport, so the same platform dependencies apply.

It checks identity `23710-2L904`, records the modeled write destinations,
checks RPM is zero, sends one mutation request without retries, receives one
frame, and requires the stop acknowledgment. It then reinitializes diagnostics
and independently reads the target and companion twice. There is no automatic
repeat or restore. If the target already contains the requested value, the
script sends no mutation because that trial could not demonstrate a change.

The output files are a timestamped `.log` (raw serial traffic) and `.json`
(plan, baseline, changes, frames and readbacks) in `logs/`. Use `--output
/path/to/trial.json` to choose a fresh report path. Existing live reports/logs
are not overwritten.

Exit codes: `0` = both readbacks match; `1` = readbacks mismatch; `2` = error or
unverified result; `130` = interruption. Offline preview also exits zero, but
its JSON status is `offline_preview`, never a hardware success.

Receiving one frame does not guarantee the ECU built only one frame. Snapshots
are serial reads taken over time, not atomic memory images. The report captures
observed changes but cannot attribute every changing status byte to the request.

## The traced example: `$0817 = $42`

Request address list (zero-based entries):

| Entries | Address | Effect |
|---|---|---|
| `0..14` | `$5E00`, repeated fifteen times | Build/overrun the forwarding arrays |
| `15` | `$5E29` | Store `$0E29` at `$07E1`, then increment low count to `$2A` |
| `16` | `$5E42` | With count `$2A`, store `$0E42` at `$07C3 + 2*$2A = $0817` |

The actual 16-bit store makes **`[$0817]=$42` and `[$0818]=$0E`**. The
same iterations also put `$0F` at `$0800` and `$10` at `$0801`; earlier
iterations modify the forwarding arrays/state. This is not an isolated byte
edit. `$0817/$0818` are current-cycle fault-flag bytes, not calibration ROM.

The trace executes the actual ROM instructions at `$543F–$54C6`, including:

1. `$5462/$5464`: read the wire-order address bytes and rotate into an address.
2. `$5477`: subtract `$5000` from a forwarded address.
3. `$5491–$549A`: calculate `$07C3 + ((2*n) & $FF)`.
4. `$54A0`: 16-bit store under `CLM`.
5. `$54A3–$54B2`: reread the potentially overwritten count and store the loop index.
6. `$54B4`: increment the count as an 8-bit value.

No data returned by the second processor supplies the `$42` in this store.
Background tasks may subsequently change RAM; that is why independent hardware
readback is required. The first downstream builder pass starts with flags
`$07E3=$0D` in the modeled example (bit 1 clear); it sets bit 1 and initializes
the cursor rather than immediately doing the `$9B5E` write. Later passes can
have further effects and are not simulated by the limited instruction runner.

Changing `--value` changes entry 16's low byte. All 256 values at `$0817` pass
the offline instruction-model test. Other odd destinations can be previewed,
but control-field aliases can defeat a requested final value; the script
rejects candidates that fail its target/companion check. This is not arbitrary
single-byte access across all of `$0740–$083F`.

## Reproduce the evidence

### Sweep values during the same key-on

Preview or test all 256 values, with the key kept on and engine off throughout:

```sh
python3 tools/c9_direct_sweep.py
python3 tools/c9_direct_sweep.py --run --dev /dev/ttyUSB0
```

To repeat the four transitions already reported from the car:

```sh
python3 tools/c9_direct_sweep.py --values FF,00,21,67 --run --dev /dev/ttyUSB0
```

There are no key-cycle prompts. **Fast mode is now the default:** identity and
initialization run once. Each value uses three short C9 reads: baseline plus
RPM together, then two independent target/companion readbacks after the mutation
has stopped. Every read and mutation requires an acknowledged stop before
reusing the initialized session. It still takes a fresh baseline and checks
engine-off before each mutation. It omits the full collateral-RAM snapshots
and per-value reinitializations; those are available with `--full-checks`.

For the default target, this reduces read transactions per value from 14 to 3,
and removes both per-value handshakes and repeated identity queries. Serial
speed and frame timing remain unchanged. Each console/CSV trial records its
elapsed seconds so actual cable/ECU performance can be measured.

The sweep stops at the first mismatch,
error or interruption, and never retries a mutation. It checkpoints a JSON
report and appends and flushes CSV results after every trial; raw serial traffic
shares the same timestamped filename stem. It does not restore the initial byte.

For a unique value list, if the first value already matches the initial RAM
byte, it moves that value to the end instead of skipping it. Thus a complete
`00-FF` sweep from an initial `$00` tests `01..FF,00`: all 256 requested values
still represent changes. Custom lists may repeat nonadjacent values, but an
already-matching baseline is never claimed as a demonstrated write. The script
does not independently establish that the operator kept the key on.

### Sweep addresses with one chosen value

Preview an address range, then write `$67` at each modeled destination:

```sh
python3 tools/c9_direct_sweep.py --addresses 0810-0822 --value 67
python3 tools/c9_direct_sweep.py --addresses 0810-0822 --value 67 --run --dev /dev/ttyUSB0
```

The full window can be selected with `--addresses 0740-083F`. For `$67`, the
current direct-store plan supports 59 candidates in that window; 197 addresses
are reported as unsupported, with reasons in JSON. The direct store puts the
chosen low byte at an **odd** address at or above `$07C3`, and `$0E` at its
even companion. It does not implement chosen `$67` writes to even addresses
or lower addresses. `$07D9`, `$07E1`, `$07E9`, and `$07EB` fail the final-state
model because of overlapping control/index stores.

Both target and companion are checked twice per attempted write. An address
already holding `$67` is recorded as `already_matches`, with **no mutation**,
and is not counted as a verified write. The CSV includes a `target` column;
the JSON distinguishes verified addresses, unsupported addresses, skips and
mismatches. The script does not restore earlier destinations, and later trials
can overwrite earlier ones as collateral effects.

Model eligibility does not establish persistence: some fields are replaced by
normal diagnostic reads, mailbox messages or control tasks. Default behavior
stops at the first mismatch. Use `--continue-on-mismatch` with `--addresses`
to record completed-but-mismatching readbacks and continue mapping the remaining
destinations. Communication errors, missing stop acknowledgments and interrupts
still stop the sweep without retrying the mutation. The broad range includes
live communications/control state; the narrower example above selects the
current-cycle fault-flag region.

### Offline instruction trace

```sh
python3 tools/trace_ram_write.py --target 0817 --value 42
python3 -m unittest discover -s tests -p test_c9_direct_test.py
```

The limited interpreter assumes bank/direct page zero, 16-bit X/Y and entry
`m=1`, matching this Consult call path. It follows `SEM`/`CLM` changes but does
not simulate interrupts, the scheduler, mailbox arrivals, or actuators.
The [saved store trace](rom-inventory/direct_write_0817_42.json) is modeled
evidence, not a hardware log.

Earlier hardware evidence for the older downstream method is in
`logs/2026-11-16_c9-tapsweep.log`, the two-tap trial has baseline `FF 01 00`
after the `F0` at line 185 and post-reinitialization readback `FF 01 93` after
line 295. That supports an observed `$0817` change to `$93`. The newer full
chosen-value result is recorded separately in the report linked above.
