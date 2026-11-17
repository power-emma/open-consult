# Engine ROM feature scan — 2026-11-16

Offline scan of `rom/23710-2L904_1000-FFFF.bin` (23710-2L904,
VQ30DE M/T), using the annotated M7700 disassembly and checking selected
instruction bytes against the binary. No serial connection or vehicle tests.

Image: 61,440 bytes, loaded at `$1000`.
SHA-256: `e91a7a83993911c1bb570ac6ddb5e998a70c710de031a0505cfc698534fd7a87`.
Both split dump files match the corresponding full-image slices byte for byte;
they are not independent confirmation that every dumped byte is genuine ROM.

## Findings

### Hidden `51`: reset-and-stream fault events, with optional sensor data

**Static code evidence; hardware behavior unverified.** This refines the existing
description in `ROM_ANALYSIS.md`, rather than discovering a new command byte.

- `$5024` accepts `51`. `$503C–$508B` immediately clears `$0810–$0822`,
  `$0E51–$0E58`, and `$0E78–$0E7A`, before `F0`. Note that the 16-bit store at
  `$5079` clears **both** `$0E57` and `$0E58`.
- Consequently, this is not a way to retrieve an intact snapshot of faults seen
  before the command. Flags set again after that clear can be reported.
- `$53A5–$53A7` allows a stored `51` command to continue into the `5A`/`C9`
  request-list parser. Conversely, `$53B6–$53BB` accepts `51` after a list has
  started. The normal parser rejects mixing `5A` and `C9` lists.
- `$9BE6–$9BEB` routes the completed data payload to `$9C04` when the stored
  command is `51`. `$9C5E–$9C79` appends fault IDs after the sensor payload,
  using `argc` for `5A`, or `argc / 2` for `C9`.
- `$9C50–$9C58` clears each flag as it reports it. `$9C80–$9C8D` caps fault
  reporting at two IDs per frame. These are single Consult code IDs, not the
  `(code, starts)` pairs returned by `D1`.

**Interpretation:** an intended live diagnostic-event channel, optionally
  multiplexed with ordinary data. It reports newly set flags, not necessarily
  every physical fault occurrence: monitor latching and scheduling still apply.
  A combined-frame decoder would need to know the base sensor-payload length.
  This scan did not establish safe capacity at maximum sensor-list length.

### Up to five active-test entries, committed together

**Static code evidence; hardware behavior unverified.** `$51A4` increments
`at_count`; `$5393–$5398` rejects another appended `0A` when the count is already
five. `$536F–$537E` copies the six requested flag bytes into the active flags on
`F0`. Values are staged earlier at `$519D`.

This supports batching compatible tests in one request. It is a limit on entries,
not necessarily five distinct tests; repeated entries also increment the count.
The parser does not establish that arbitrary actuator combinations are valid.

### Existing underused capabilities corroborated by the parser

| Capability | Evidence | Qualification |
|---|---|---|
| Up to 40 `5A` register entries | `$53BF–$53C4`, `$5103–$5106` | Argument-byte limit; not car-tested here |
| Separate `0A` direct-data mode | `$5112–$5115`, `$51C6–$5237`, `$9CDD` | Selectors 0, 2, 5, 6, 7 have explicit zero-value branches; OBD Mode 6 identity remains inferred |
| Special handling when stopping test `AA` | `$5406–$540B`, `$550A–$5513` | Preserves backup bits 7–6 during that reset and consumes bit 4; not proof of preservation through power loss |
| Configuration-selected alternate ISR | `$4EFA–$4EFF` | ROM `$1206 = 00`: branch to `$017B08` disabled in this image |

## Scope and limits

The ordinary command dispatcher contains `FF`, `30`, `C9`, `5A`, `0A`, `51`,
`D1`, `C1`, and `D0`; no additional top-level opcode was found in that path.
That does not exclude features in unread code or another processor.

The `$5D40–$623F` dump region is already identified as forwarded/stale data,
not trustworthy local ROM. Bank 1 is absent. The 768-byte BCM fragment and the
small H8 reconstruction were not treated as complete firmware.

Existing overflow/write and hidden-read claims were not revalidated by this
feature scan. `ROM_ANALYSIS.md` references `docs/processor-write/FINDINGS.md`
and `SESSIONS.md`, but neither file exists in this checkout. Its older broad
conclusions about reachability should therefore not be treated as settled here.

Next useful validation is a recorded bench trace of `51` alone and combined with
a short read-only sensor list, using a deliberate known monitor condition and
checking event placement, clearing, and frame lengths. No new actuator probing
is needed to validate that interpretation.
