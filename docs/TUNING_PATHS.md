# Routes from Consult access to engine tuning

2026-11-16, ECU 23710-2L904. The immediate objective is an observed,
laptop-controlled change to an engine-control term, followed by repeatable
parameter updates. A permanent ROM-map edit is a separate capability.

## Most direct candidate: native fuel-feedback override

There is no need to redirect execution to request a fuel-feedback percentage:
test `81` has an ordinary descriptor and a visible bank-0 implementation.

| Evidence | Meaning |
|---|---|
| `$6E15` | Active flag `$07B7.1` selects the override |
| `$6E1A–$6E27` | Read `$0770`, clamp to decimal 75..125 |
| `$6E29–$6E2B` | Replace the current bank's feedback working word |
| `$7434–$7439` | Select that overridden term for reporting/control |
| `$7440–$7451` | Store it to `$0730` or `$0731`, selected by the bank flag |
| `$4D15/$4D47` | Call the feedback routine for the two bank working blocks |

The existing CLI can already send a timed `fuel-trim` active test. The new
`tools/fuel_control_test.py` adds simultaneous readback of both alpha values,
RPM, load code, injector pulse widths, active-test flags, the parameter byte
and vehicle speed. It requires the final three telemetry samples of a step to
show the requested value in both banks and requires the override flag to clear
after STOP. An echo or parameter-byte match alone does not pass the test.

The candidate combined request is native `0A 81 <percentage>` followed by 13
local-RAM `C9` reads and `F0`. In the parser, an active-test entry can be followed
by a C9 list (`$53A0–$53E8`); `F0` commits the test flags (`$536F–$537E`) and
the C9 flag selects the data reply (`$9AD6`). The request consumes 28 argument
bytes, below the 40-byte gate; none of its read addresses is forwarded, so it
does not trigger the forwarding-array overrun. This combined form is traced
from the visible parser, **not yet demonstrated by a hardware capture**.

Preview:

```sh
python3 tools/fuel_control_test.py --percents 100,103,100
```

Bounded live test, with the engine running so its feedback routines execute:

```sh
python3 tools/fuel_control_test.py --percents 100,103,100 --seconds 2 --run --dev /dev/ttyUSB0
```

Each step ends with acknowledged STOP. The script checks engine RPM before
requesting each step, logs the serial traffic and telemetry, and stops at the
first unverified step. It does not automatically retry a changing command.
The last serial frame can extend a hold slightly beyond the requested time.

This is a **temporary feedback-term replacement**, not a permanent tune or a
guaranteed percentage change in measured air/fuel ratio. A baseline feedback
term may not already be 100; load, learning, operating mode and other fuel
terms still matter. Injector telemetry and bank readbacks provide evidence
of application, not an independent mixture measurement.

If the mixed command is rejected, that is a concrete parser/transport result
to investigate; the tool does not silently declare a successful tune or use an
unverified fallback. The current streaming parser accepts only `FF` or `30`,
so parameters cannot simply be injected into an active stream.

### Implemented laptop RPM/load controller

`tools/laptop_fuel.py` now supplies the software side of a table-driven
controller. **Its hardware control path remains pending the test above.**
It leaves an unchanged percentage streaming, verifies three matching samples
before accepting it as applied, and uses acknowledged STOP, fresh RPM/load
readback and a new request when the map selects a different percentage.
Every request is single-attempt. Missing frames, unapplied percentages,
invalid reloaded maps and engine-off terminate control with a STOP attempt.
Final success also requires the active flag to be read back clear.

Preview a constant native percentage or the stock-control map:

```sh
python3 tools/laptop_fuel.py --fixed-percent 103
python3 tools/laptop_fuel.py --map maps/native-fuel-stock.json
```

After the mixed command and bank readbacks are confirmed, bounded live runs:

```sh
python3 tools/laptop_fuel.py --fixed-percent 103 --seconds 10 --run --dev /dev/ttyUSB0
python3 tools/laptop_fuel.py --map maps/native-fuel-stock.json --reload-map --seconds 60 --run --dev /dev/ttyUSB0
```

The supplied map has **no tuned values**. Its `null` cells leave feedback under
normal ECU control; replacing cells with numbers requests the corresponding
native percentage. Rows correspond to `load_code_axis` and columns to
`rpm_axis`. The load coordinate is the raw `$0ABE/$0ABD` word, not an assumed
physical pressure or verified percentage. Telemetry logs expose that coordinate
for choosing appropriate breakpoints.

The lookup interpolates bilinearly, clamps outside the axes and rounds to a
whole percentage. A positively weighted `null` corner selects normal ECU
control; zero-weight `null` corners do not disable an exact configured node.
`100` is a fixed feedback override, not a synonym for stock operation.

Use an atomic file replacement when editing a map with `--reload-map`: an
invalid partial JSON file ends the run rather than continuing with uncertain
settings. Logs include raw traffic, each requested control state, the map
hashes, request verification times and per-frame samples in `.samples.jsonl`.
Observed STOP-to-request-ack times are recorded on transitions. They do not
establish the exact engine-control gap; that and achieved update rate require
hardware measurements. The firmware's normal control runs between stops and
new requests, so uninterrupted fixed-percentage application is not promised
during map changes or after a lost connection.
The bounded duration is enforced by the laptop, not an ECU watchdog. If the
link fails and STOP cannot be acknowledged, this tool cannot guarantee that
the ECU has released the fixed-feedback override.

## Which reachable fields really are pointers?

| RAM field | Consumer | Capability and limit |
|---|---|---|
| `$07C3–$07D6` | `$9B75–$9B7B`, then `$CD62/$CD67` | Forwarded data-address words. Hardware reports show `$0E67` successfully planted at multiple entries. They select second-processor reads, not executable code. New forwarded-list setup normally replaces them. |
| `$07D7–$07E0` and out-of-array indices | `$9B4F–$9B5E` | Placement offsets: choose a destination in `$0740–$083F` for the current `$07E7` byte. These are indices, not full addresses. Chosen-value control of this downstream source has not been established. |
| `$07E4/$07E5` | `$CD62–$CD6A` | Next second-processor read address. Rebuilt by the reply builder at `$9B7B`; direct writes here do not establish a persistent pointer. |
| `$07A0–$07AB` | `$9CF1–$9CF7`, `$9D10–$9D15` | Local bank-0 data-read pointers. A controlled entry could expose local code in the C9 forwarding hole, but the current direct-store base is `$07C3`, above this list. Mode setup also replaces the list. Still an open chaining problem. |
| `$07FD/$07FF` | `$BBC9/$BBD9`, `$BC29–$BC68` | **Not pointers:** scalar lower/upper bounds on idle-adaptation state `$04A1`. A plausible control influence, but not an address-redirection primitive. |
| `$080A/$080C` | `$8A53/$8A59` | Loaded into X as sample/history data. Loading X is not proof that a word is later dereferenced as an address. |

Existing logs `2026-11-16_202802_513287_address-sweep.json` and
`2026-11-16_202820_137964_address-sweep.json` support pointer-byte planting
in the forwarding list. They do not establish a chosen second-processor result
or a bank-1 dump. The `$07E7` trial in
`2026-11-16_202855_860849_address-sweep.json` read back `$00`, not the requested
`$67`, and its companion `$07E8` became `$02`, not `$0E`. That is direct evidence
against treating the reply-source byte as persistent chosen data.

The decoded bank-0 listing has one indirect instruction transfer:
`JMP ($CBAB,X)` at `$CAF1`, through a bounded nine-entry ROM table. Its targets
are not in the writable region. This is **no identified RAM-code-pointer route**,
not proof that code redirection is impossible in unread bank 1 or absent code.

## Further reach to investigate offline

The direct-store instruction's mathematical destination range is larger than
the conservative live test interface: `$07C3 + ((2*n) & $FF)` reaches word
starts through `$08C1` (second byte `$08C2`). The index store separately reaches
`$07D7+n`, through `$08D6`, but writes the small iteration number rather than a
chosen arbitrary byte. These formulas do **not** expand reach down to `$07A0`
or up to the `$0Axx/$0Bxx` fuel/timing working variables.

There may be useful flags in that extra `$08xx` portion, but companion and
index collateral stores must be traced before expanding live tests. No live
testing above the current direct-test target limit is implemented here.

The calibration-shadow region `$0390–$048F` is likewise outside the current
write paths. Base timing/fuel-map readers and the main loop include missing
bank-1 code. A durable ROM-map tuning route needs a confirmed map writer,
external memory interface, or trustworthy full chip image and programming path;
none is demonstrated by a successful `$0817` RAM write.

## Current status

- Chosen RAM byte values at `$0817`: hardware-confirmed for all 256 values.
- Other destinations: individual hardware readbacks exist; background updates
  and deterministic collateral stores explain differing persistence.
- Native fuel override: parser and both-bank consumer traced; bounded control
  test plus RPM/load laptop controller implemented and tested offline; hardware
  application and achievable live update rate pending.
- Direct-data pointer redirection, timing control semantics, persistent map
  edits, and continuous laptop-table control remain unverified.
