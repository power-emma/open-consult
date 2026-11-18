# Cross-generation A32 bank-call comparison

The available 1996 A32 images do **not** include a bank-1 code image. The
decoded 1996 `54U03` bank-0 image makes 90 direct `JSL $04xxxx` calls and no
decoded `JSL $01xxxx` calls. The Nistune pack provides a separate `54U01`
`BANK2.bin`: this second ROM image contains the code at the `$04xxxx` targets
called by the matching `54U01` bank-0 image. The pack has no A32 bank-1
`.bin`; its only file named `bank1` is for a Z32, a different ECU family. The
1997 `0L701` and 1998 `2L904` bank-0 images each contain direct calls into
unavailable bank 1.
Nistune's [Type 4 hardware guide](https://www.nistune.com/docs/NIStune_Type_4_Hardware_Installation.pdf)
also lists the 1996 A32 as using a dual-ROM board.

## Matched caller locations

These matches compare the caller bytes around each `JSL`, excluding its four
bytes. A score of 23 means 23 equal bytes in the 25-byte context used for the
1997-to-1998 comparison. It is evidence that the *caller* is homologous; it
does not supply the called routine's bytes.

| 1996 bank 0 caller → bank 4 | 1997 bank 0 caller → bank 1 | 1998 bank 0 caller → bank 1 | Inference |
|---|---|---|---|
| `$42DA → $048C49` | `$42D8 → $014728` | `$3FE3 → $01428D` | Shared call-site role across three generations |
| `$42E5 → $048C23` | `$42E3 → $014715` | `$3FEE → $01427A` | Second shared call-site role |
| `$4E3C → $04B376` | `$4F38 → $016F52` | `$4CEE → $016FA7` | Bank-4-to-bank-1 architectural migration |
| No matching decoded call | `$8B4F → $015DC9` | `$8A85 → $015AD1` | Exact sample-history caller in 1997/98 only |
| No matching decoded call | `$8B5C → $015DC9` | `$8A92 → $015AD1` | Same helper called with a second constant |

The 1997/98 pair at `$8B4F/$8A85` has 23 equal context bytes; the next-best
1998 candidate has 5. The second call pair has the same 23-versus-5 margin.
No decoded 1996 bank-4 call has a comparable caller match to either 1997
sample-history call (best context score 3 in a wider 33-byte comparison).

The first two 1996 targets can be read in `54U01_1996_MT_BANK2.bin`.
`$048C49` loads calibration words at `$FAB1/$FAB0`, masks them, and stores
bounds at `$3660/$365E`. `$048C23` compares its incoming accumulator with
those bounds and returns a clamped result/status. These are concrete numeric
predecessors for the matched call-site roles; their behavior cannot be
transferred to the unrelated sample-history helper.

Among decoded 1996 bank-0 calls, the short repeated-target pairs use
`$044000`, `$044016`, `$048C23`, or `$04499F` (and their `54U03` relocations).
None has caller bytes resembling the 1997 `$8B4F/$8B5C` pair. This is a
negative result for a direct 1996 predecessor, not proof that the underlying
algorithm was absent elsewhere.

The corresponding bank-1 targets do not share one relocation offset:
`$014728 → $01428D` moves by `-$049B`, while `$015DC9 → $015AD1` moves by
`-$02F8`, and `$016F52 → $016FA7` moves by `+$0055`. Therefore a constant
address translation cannot predict the missing 1998 helper body. The direct
calls are code destinations, not RAM-controlled function pointers. The
decoded 1998 bank-0 control-flow audit found no unbounded indirect bank-1
transfer; it cannot rule out pointer use inside unread bank 1.

**Result:** 1996 bank-0 pointers establish continuity and a bank-4-to-bank-1
layout change. The 1997 caller establishes that `$015AD1` is the relocated
sample-history helper `$015DC9`. Neither image exposes its implementation or
shows an indirect read/write through `X`. A bank-1 code image or an observed
hardware response is still required to determine that behavior.

Pre-mutation hardware reads in
`logs/2026-11-16_203034_567387_address-sweep.json` and neighboring sweep
reports show `$080A=$4E` and `$080B=$4E` when the engine is off, while
`$080F` was zero before its own write trial. The snapshots are not atomic, so
they do not prove the helper's exact call-time inputs. They do support the
ordinary interpretation that `X` packs sample bytes: treating the common
`$4E4E` pattern as a memory address would point into ROM code. This makes an
indirect-pointer interpretation less plausible, but does not exclude it.

Earlier read-only RAM dumps give a stronger gate check. In
`rom/ram_0080-0FFF_1.bin`, `$088B=$41`, `$092A=$C5`, `$0CA5=$FF`, and
`$0717=1`; in `rom/ram_0080-0FFF_2.bin`, the first three values match and
`$0717=4`. A subsequent register watch in the same raw session logged RPM
zero. Replaying the fixed-X request-builder model from the second RAM image,
then executing visible bank-0 instructions from `$8A50` to the call, reaches
`$8A85` with `X=$080E`, `A.low=$0A`, and `[$080E]=$31`. Replaying from the
first image exits at `$8AC6` because its counter has not yet reached five.
This makes an engine-off call plausible in a verified session, while leaving
the hidden helper and live request timing unobserved.

The two raw RAM-dump frames at `$0808-$080F` were respectively
`80 FF 75 75 75 75 75 00` and `80 FF 74 74 74 74 74 01`. Later reads of
`$0C98-$0C9F` in those same sessions gave `$0C9D=0` and `$0C9D=1`.
These values are consistent with a numeric sample-difference calculation;
the reads are seconds apart and do not establish its exact equation.

Input images: `rom/23710-2L904_1000-FFFF.bin`,
`rom/reference/nistune-2.14/extracted/app/ROM_Pack/Type34/A32_VQ30DE/A32_VQ30DE_0L701_MT_1997.bin`,
`A32_VQ30DE_54U01_1996_MT.bin`, and
`A32_VQ30DE_54U01_1996_MT_BANK2.bin` in that same reference directory.
