# Engine firmware atlas — 23710-2L904

This is an expanding explanation of what the available firmware does, with a
structural inventory that keeps unknown code visible. It is not a complete
decompilation. Analysis below is offline, dated 2026-11-16.

**Evidence levels:** “code” means supported by visible instructions; “inferred”
means a physical interpretation of those instructions; “unavailable” means the
necessary instructions are absent from this dump. Hardware validation is separate.

## First, corrections that change the interpretation

### `$09AE` is RPM, not load

The old notes repeatedly describe `$09AE` as load. The assignment chain at
`$5665–$5685` establishes otherwise. Let `R` be the 16-bit RPM word exposed by
Consult registers `00/01` (RPM = `12.5 × R`):

| RAM | Exact assignment in visible code | Interpretation |
|---|---|---|
| `$09AE` | `min(R, 255)` | RPM in 12.5-rpm units, capped at 3187.5 rpm |
| `$09B0` | `min(R >> 1, 255)` | RPM in 25-rpm units, capped at 6375 rpm |
| `$09B1` | low byte of `R >> 2` | RPM in 50-rpm units; no saturation in this store |
| `$0ABD/$0ABE` | Separate word used by fuel scaling | Existing load/CAL-LD interpretation; not established by the RPM chain |

This changes readings of idle control, purge enables, knock enables and P1320
preconditions. For example `$09AE >= $20` means approximately **RPM >= 400**,
not “load >= 32.” `$09AE >= 4` means approximately **RPM >= 50**.
Logged correlations previously attributed to load need reanalysis before using
them to diagnose the car. This correction does not change the raw logs.

### Rejected test `83` is an idle-speed-target override

**Code:** `$B39A` tests active flag `$07B7.3`, takes `$0772`, caps it at `$90`,
and stores `$0BCD`. `$AD19–$AD4A` moves `$0BCB` toward `$0BCD` in single-code
steps with a counter-controlled cadence, or copies the target on another path.
The idle feedback loop compares `$0BCB` with actual RPM code `$09AE`.

**Strong interpretation:** `$0BCD` is desired idle speed in 12.5-rpm units;
the override cap is **1800 rpm**. The normal target routine starts at `$B21D`;
its temperature table at `$2150` includes `$32` = **625 rpm**, matching the
M/T warm-idle specification in the local FSM (`reference/EC_ocr.txt`, EC-84).
Its 16 raw entries are:

`64 64 63 63 62 61 61 60 5C 52 46 32 32 32 38 38`.

This is different from test `85`, which overrides the applied air-valve step.
The descriptor for `83` at `$1166` is `FF FF`, so the ordinary command parser
rejects it. A dormant handler does not establish a supported command or a
tested way to invoke it. A target does not guarantee the engine reaches that speed.

### `A2`: pressure-selector override; “engine mount?” is poorly supported

**Code:** `$F471` reads ADC channel `$0B`, stores raw/scaled pressure samples
at `$0D79/$0D75`, and calls a baseline calculation at `$F69E`. `$F4C0` checks
test `A2`: zero goes to the clear path, nonzero to the set path for `$095D.2`.
The normal sequence samples the filtered signal in both output states:

| Step | Evidence |
|---|---|
| Set output and reset settling counter | `$F55E–$F56B` |
| After settling, save one sample to `$056A` | `$F571–$F583` |
| Clear output and reset settling counter | `$F58D–$F596` |
| After settling, save the other sample to `$0D77` | `$F59C–$F5AA` |
| Compute nonnegative sample difference | `$F5B2–$F5C4`, result `$08A9` |
| Out-of-range or failed functional check | `$F5E9/$F668`: detect slot `$3A`, **P0105** |

**Strong inference:** this is associated with switching the absolute-pressure
sensor between manifold and barometric pressure. The local FSM describes that
arrangement for P0105 (EC-117). Physical pin tracing is still needed to name
the `$095D.2` actuator conclusively. The older `$095E.1 = MAP/BARO` assignment
also needs review: `$E7A2` samples another input (`$09FC`, ADC `$0C`) around
that output's transitions. It is a separate sequence, not interchangeable evidence.

## How the firmware runs

### Reset, validation, and transfer to missing code

| Entry/path | Visible purpose | Limit |
|---|---|---|
| `$3D75` reset | Set direct page/data bank, serial configuration and stack `$0FFF` | Exact CPU derivative still uncertain |
| `$3DAA–$3DBE` | Clear `$0700–$08F9` and `$0E80–$0F79` | Those ranges are explicitly cleared at this reset |
| `$3E18` onward | Configure ports, timers and peripheral defaults | Register names beyond the annotated I/O require chip identification |
| `$3F87–$3FFD` | Check retained-RAM marker, byte checksum or calibration-shadow bounds | Failure calls unavailable bank-1 `$015803` |
| `$4002` | First ADC acquisition and state setup | Some initialization helpers are in bank 1 |
| `$431D` onward | Enable interrupts and initialize pressure/control state | Do not infer actuator pin names from port bits alone |
| `$4472` | Jump to **`$010000`** | Main-loop implementation is unavailable |

The main loop is not fully present in this file. Bank 1 is called during normal
operation; it is not merely an optional hidden diagnostic extension.

### Interrupts and scheduling

| Entry | Role established by visible effects |
|---|---|
| `$4797` INT2 | Crank REF capture, ignition target construction and scheduling |
| `$4A3A` helper | Advance 0–5 cylinder counter and build coil-fire mask |
| `$4495` Timer A3 | Apply queued coil mask through output routine `$C502` |
| `$46C0` Timer A2 | Dispatch crank/timing event flags; full physical mapping incomplete |
| `$4540`, `$44B6` | Knock-interface programming/readback and watchdog work |
| `$4BC2` UART0 TX interrupt | Scheduler tick, vehicle-pulse history and task arming |
| `$4EF5` UART1 RX/TX | Consult receive parser and transmit state machine |
| `$473F` NMI | Exception path; complete physical trigger unresolved |

The scheduler counter `$096A` cycles through ten slots. Pending bits in `$092E`
select groups, in priority order `04`, `10`, `40`, `20`. Dispatch clears a bit,
enables interrupts, executes the group and checks again. `$092C.6` and `$096B`
provide an active-dispatch guard and deferred-tick accounting (`$4C2E`, `$4E3A`).
Absolute periods in milliseconds have not been derived from a verified CPU clock.

| Group | Trigger | Work |
|---|---|---|
| `04` | Odd slots | MAF ADC read (`$551F`) |
| `10` | Slots 1 and 6 | RPM, throttle history, fuel calculation and injector pulse construction |
| `40` | Armed by REF handler at `$4B9C` | Per-bank oxygen feedback/adaptation and associated checks; conditional bank calls |
| `20` | Slots 3 and 8 | Switches, diagnostics, mailbox receive/send, Consult, knock, idle, purge and output updates |

Every direct call inside these groups is listed in
[`scheduled_calls.csv`](rom-inventory/scheduled_calls.csv), including calls into
the dump hole and bank 1. Calls listed within a group can still be conditional.

## Engine-control paths

| Subsystem | Main visible entries | What can be explained now | Still unresolved |
|---|---|---|---|
| RPM | `$5624` | History shift and RPM-derived indices; scaling above | Upstream timer details/clock verification |
| MAF | `$551F`, `$5531`, `$5558` | ADC acquisition, voltage/flow processing, scaling | Full physical calibration validation |
| Throttle | `$F19E`, `$5849`, `$5B92` | ADC, filtered absolute position and sample history | All derivative thresholds and transient flags |
| Battery | `$F1DE` | Sampling/filtering and diagnostic state | Full compensation path and thresholds |
| Fuel quantity | `$644C`, `$66BA`, `$683A`, `$68F3` | Load/quantity scaling and intermediate corrections | Exact semantics of all terms and missing bank-1 maps |
| Injector pulse | `$6A20`, `$C502` area | Bank pulse calculation, cylinder trims, saturating math; timer-output code | Full timing/event-to-pin derivation |
| O2 feedback | `$6D65` | Separate bank working blocks; rich/lean feedback, RPM/speed hysteresis, alpha override | All learning cells and transition state meanings |
| Ignition | `$4797`, `$47A8`, `$4495` | Timing target, rate limiting, cylinder trims and coil mask | Base map lookup in missing code |
| Knock | `$9EDA`, `$9F27`, `$A1FC` | Active-zone gates, retard working state, fail-safe paths | Complete chip protocol and second-CPU monitor implementation |
| Idle air | `$AC54`, `$B21D`, `$B3AC` | Speed target, target ramp, load compensation paths, applied-step override | Full fixed-point controller derivation |
| Purge | `$BD00`, `$BFB3`, `$C038`, `$9488` | Purge accumulation, step lookup, test override, phase outputs | Exact rate units and every enable flag |
| Pressure selection | `$F468–$F6FE` | Paired pressure sampling, baseline and P0105 checks | Pin confirmation and alternate `$F6FF` variant |
| Other switched-pressure check | `$E7A2`, `$E819` | Change `$095E.1`, average eight samples of `$09FC`, save three results | Physical sensor/valve identity |
| Output images | `$4E61`, `$9D3F` | Push software output images to ports/mailbox; pack Consult status | All physical bit-to-pin mappings |

Map addresses `$1400`, `$1700`, `$1800`, `$1D00`, `$1E00` retain the existing
VE/fuel/knock-fuel/timing/knock-timing interpretation. Their shape and previous
reference matching are not a substitute for tracing their unavailable consumers.

## Diagnostic paths and less-visible features

The Consult parser and fault-event behavior are detailed in
[`ROM_FEATURE_SCAN.md`](ROM_FEATURE_SCAN.md). Its `51` event stream clears the
current-cycle flags immediately, then reports newly set flags, with a maximum
of two fault IDs appended per frame. Ordinary DTC `D1` is a different format.

The complete 46-entry active-test descriptor range (22 supported, 24 unsupported),
is in [`active_tests.csv`](rom-inventory/active_tests.csv). Descriptor existence
does not identify the physical actuator. Handlers in bank 1 remain unavailable.

Fault storage has separate pending, confirmed, history and per-cycle arrays.
`$DE86` handles a detection; `$D371` confirms it; `$DFBB` captures conditions;
`$DC52` captures a freeze frame. The 152 slots, code IDs, P-codes and counter
pointers are in [`dtc_slots.csv`](rom-inventory/dtc_slots.csv). A table entry
can exist for equipment absent from this calibration.

### `AB` exposes monitor admission status, not just a mystery sequence

At `$986A` the ECU builds `$0F6F` as a **blocking-condition bitfield**.
`$98E6` selects the lowest set bit and maps it through `$9913` to `$0F6D`
(Consult register `61`); no set bits produces zero.

| Blocking bit | Condition in visible code | Reported `$0F6D` |
|---|---|---|
| `01` | `$0931.2` set | `83` |
| `02` | `$0F6E > ROM[$2BDE]` | `86` |
| `04` | Battery code below ROM `$2BD9` | `81` |
| `08` | `$097F < ROM[$2BDD]` | `85` |
| `10` | `$0858 < ROM[$2BDA]` | `82` |
| `20` | `$0872` outside `[ROM[$2BDB], ROM[$2BDC])` | `84` |
| `40` | Active-test status `$07F1.2` set while `AB` flag is clear | `80` |
| `80` | `$092A.6` clear | `87` |

`$991B` combines the test value `$079A`, state bits `$0F6C`, and incoming
`$07EB.0`. A zero status allows a completion/permission bit to set. Therefore
calling register `61` only a “sequence step” misses its explicit admission-error
encoding. Names/units of every prerequisite are not yet established.

### Nine internal requests from the second processor

`$CAD7` searches nine request IDs and dispatches through `$CBAB`. It returns
two bytes in `$07FB/$07FC`, clears `$07F9`, and sets response-ready `$07F1.4`.
This is a separate internal interface, not nine additional Consult commands.

| Request ID | Returned first byte | Returned second byte |
|---|---|---|
| `20` | RAM `$0307` | ROM `$23BC` or `$23BE`, selected by config `$1207.6` |
| `21` | RAM `$0308` | RAM `$030C` |
| `60` | RAM `$04C9` | ROM `$25AA` |
| `61` | RAM `$04CA` | RAM `$030E` |
| `A0` | RAM `$04CB` | ROM `$2362` |
| `A1` | RAM `$04CC` | ROM `$2363` |
| `A2` | RAM `$04CD` | ROM `$2364` |
| `A3` | RAM `$04CE` | RAM `$056E` |
| `A4` | RAM `$04CF` | ROM `$2361` |

Unknown requests clear the response bytes and response-ready bit (`$CAF4`).
The request meanings are not yet identified. Similar numeric IDs do not imply
the same meanings as Consult active tests.

## Coverage, decoder correction, and reproducibility

The disassembler formerly walked past the nine pointers at `$CBAB–$CBBC`.
Adjacent instructions at `$CBBD` happened to resemble more ROM pointers,
creating phantom code at `$2020` and overlapping decodes at `$A977`. The walker
now respects annotated table sizes. The annotated listing was regenerated;
there are no overlapping instruction bytes or missing in-image direct branch
targets in the resulting structural checks. This does not prove every decode.

Run:

```sh
python3 tools/m7700dis.py rom/23710-2L904_1000-FFFF.bin --ann rom/23710-2L904.ann -o rom/23710-2L904.asm
python3 tools/rom_inventory.py
python3 -m unittest discover -s tests -p test_rom_inventory.py
```

The inventory includes direct transfer sites, called/vector entries, literal
memory references, configuration references, scheduled calls, tests, fault slots,
and byte-range classification. See [`summary.json`](rom-inventory/summary.json)
for current counts. “Decoded” means instructions were recovered, not that their
purpose is understood. Unclassified bytes may be data, padding, or missed code;
the tool does not turn them into invented functions.

For every decoded jump, call, taken conditional branch and vector reference, use
the [destination/source cross-reference](rom-inventory/JUMP_XREFS.md). It includes
the nine resolved jump-table edges and long transfers to missing banks.
Regenerate it with `python3 tools/rom_control_flow.py`.
The specific [check for transfers to/from `$0740–$083F`](ROM_JUMP_WINDOW.md)
found no matches in the decoded control flow; missing-code and runtime limits apply.
The [direct RAM-write test](../write-access/docs/DIRECT_RAM_WRITE_TEST.md) traces a chosen-value
word store at `$54A0` and provides an offline preview/live readback script.

The missing `$5D40–$623F` local-ROM region, bank 1, and second-processor program
prevent a complete account of everything from this image alone. The reset jump
to `$010000` and routine bank-1 calls are direct evidence of that gap.

Highest-value remaining work is to derive the idle controller and temperature
indices fully; map mailbox fields and status bits; identify all monitor call
sites; then trace fuel/ignition terms against the RAM and calibration tables.
Unread code needs an additional trustworthy dump before its behavior can be named.
