# Write primitive: what it can do

> **20-address write primitive (2026-11-16):** `tools/c9_write.py` computes
> payloads that write a chosen byte to a chosen address in `$0740–$083F`.
> Position 18 sets `c9_sub_value` via the direct addr_store *before* the
> reply builder or H8 can overwrite it, solving the value-control problem
> that blocked the 18-address actuator test.  `consult_reset` clearing
> `at_active` on stop also prevented post-stop readback of those targets,
> but the preserved actuator captures show no confirmed target-address
> change during any trial ([SKEPTICISM.md](docs/processor-write/SKEPTICISM.md)).
> Targets in `at_values` (`$076F–$079C`) and other ranges NOT cleared by
> reset can be verified by post-stop readback.  **Hardware verification is
> pending; the downstream write mechanism is unconfirmed on hardware.**
>
> Previous notes: [evidence and limits](docs/processor-write/SKEPTICISM.md),
> [findings](docs/processor-write/FINDINGS.md),
> [preserved sessions](docs/processor-write/SESSIONS.md).

Summary of capabilities and limits of the `c9_find_hidden` buffer overrun
(ROM_ANALYSIS.md §10) on the 23710-2L904 engine ECU.

## The primitive

Send 16–20 C9 addresses all inside `$5D40–$623F`, then `F0`. The ECU's
`c9_hidden_addr` and `c9_hidden_idx` arrays hold 10 entries each, but the
loop has no upper-bound check — the only terminator (`$54C0`:
`ASL A; CMP $073B; BCC`) compares against `cs_argc`, not array capacity
(ROM_ANALYSIS.md §10). From `i = 10` the stores walk off the end into
live handler state.

**Hardware evidence:** [overrun log](logs/2026-11-15_c9-overrun-test.log),
session 17:27:29 — baseline `$07E2–$07E5=$00`, `$0817=$00`; after 16×`$5D40`
and three frames: `$07E2=$03`, `$07E3=$0C`, `$07E4=$40`, `$07E5=$0D`,
`$0817=$0F`. The `$0817` change matches the predicted redirected index store
(n corrupted to `$40` → `$07D7+$40=$0817`, value=15).

Two stages:

1. **Direct overrun** (`c9_find_hidden`, `$543F`): the 16-bit addr store
   `STB $00,X` at `$54A0` (under `CLM` from `$5495`, so 16-bit stride) and
   the 8-bit index store `STA $00,X` at `$54B2` (under `SEM` from `$54AE`)
   walk past the arrays. At `i = 15` the addr store destination is
   `$07C3 + 2·15 = $07E1`, writing a caller-controlled word into
   `c9_hidden_n` and the reply cursor. The 20-address payload uses
   positions 15–18 to repair `$07E3`, set the target index, and pre-load
   `c9_sub_value` — all via the direct overrun. **Hardware-confirmed**
   (overrun log above).

2. **Downstream OOB** (`consult_reply_c9`, `$9B3F`): the per-frame store
   at `$9B5E` (`STB $00,X` where X = `$0740 + c9_hidden_idx[cursor]`)
   writes `c9_sub_value` through a corrupted index, escaping the 40-byte
   payload buffer into `$0740–$083F`. **Simulation only — not yet confirmed
   on hardware** (see [timing concern](#timing-concern) below).

## The 20-address controlled write (`c9_write.py`)

```
[0..14]  15 × $5E00            fill arrays normally, overrun at i=10+
[15]     $5E0A  (repair_a)     addr→$07E1: n=$0A, cursor=$0E; idx→$07E1=$0F; INC→$10
[16]     $5E0B  (repair_b)     addr→$07E3=$0B (bits 0+1 set); idx→$07E7=$10
[17]     $5E00+T  (target)     addr→$07E5=T (idx[$0E] = target offset)
[18]     $5E00+V  (value)      addr→$07E7=V (c9_sub_value = desired byte!)
[19]     $5E00    (dummy)
```

Where `T = target_addr - $0740` and `V = desired byte value`.

**Position 18 is the key advance.** After i=17 leaves `n=$12`, i=18's
addr_store destination is `$07C3 + 2·$12 = $07E7` — it writes the chosen
value byte directly into `c9_sub_value` via the overrun's own store
instruction, *before* the reply builder runs and *before* any H8 reply can
arrive. The earlier 18-address actuator test could only set `c9_sub_value`
to the loop counter ($10), limiting it to one value.

**Verified by simulation** (`consult/write.py`): all 65,536 target/value
combinations produce the correct overrun state. The addr_store arithmetic
follows directly from the ROM at `$54A0` and the 16-bit stride under `CLM`.

The builder's first frame then reads `c9_sub_value = V` (`LDB $07E7` at
`$9B3F`) and writes it to `cs_payload[idx[$0E]]` (`STB $00,X` at `$9B5E`)
= `cs_payload[T]` = `target_addr`.

**Unresolved timing risk:** the builder gate at `$9B2F` checks the mailbox
handshake bit (`$029E.4`) — if the H8 handshake is pending, the builder
skips entirely. And `mailbox_receive` at `$C862` writes `$07E7` with the
H8's response byte; if it runs between the overrun and the builder's read,
the pre-loaded value is destroyed. See [timing concern](#timing-concern).

## Constraints

| Constraint | Detail |
|---|---|
| Destination range | `$0740–$08D6` (~275 bytes) via the direct overrun; `$0740–$083F` (256 bytes, arbitrary byte) via the downstream write |
| Value range (direct) | 16-bit word in `$0D40–$123F` (low byte free, high byte pinned `$0D–$12`), or the loop counter (0–19) |
| Value range (downstream) | Any byte `$00–$FF`: position 18 sets `c9_sub_value` directly |
| Persistence | Direct overrun state survives re-init; key cycle clears. Downstream write to `at_active`/`at_req` is cleared by stop (`consult_reset`); writes to `at_values`, `cs_streamlist`, and `$07BD+` persist through stop |
| Code execution | Impossible — no RAM function pointer exists anywhere in the image (ROM_ANALYSIS.md §10) |

### Why the 18-address actuator test failed

Two known contributing causes, neither independently confirmed:

1. **Value control:** `c9_sub_value` was only set to $10 (the loop counter
   at position 16), not a chosen byte.

2. **Reset wipe:** `consult_reset` (called on stop) clears `at_active`
   (`$07B7–$07BC`) and `at_req` (`$07AC–$07B1`).  Any successful write to
   those ranges would be wiped before post-stop readback.

The preserved actuator captures show no target-address change in any trial.
The sustained `$02/$0B` seen in frame probes are reply-payload bytes, not
independent readback of destination RAM
([SKEPTICISM.md](docs/processor-write/SKEPTICISM.md),
[FINDINGS.md](docs/processor-write/FINDINGS.md)).  A model/hardware
disagreement remains unexplained.

## What works

> **Evidence key:** items below are marked **(hardware-confirmed)** when
> independent readback on the ECU shows the predicted change,
> **(simulation only)** when the model predicts it but no hardware test
> succeeded, or **(hardware-failed)** when a hardware attempt contradicted
> the model. See [SKEPTICISM.md](docs/processor-write/SKEPTICISM.md) and
> [FINDINGS.md](docs/processor-write/FINDINGS.md) for the full evidence
> review.

### 1. Write to `cs_streamlist` + read hidden code (`$5D40–$623F`)

**(Simulation only; hardware attempt failed.)**

The ROM analysis (§11) flagged `cs_streamlist` as unreachable from Consult.
The overrun's downstream OOB *can* reach it — and chains with the
`consult_reply_direct` read bug to read the main CPU's hidden code.

`consult_reply_direct` (`$9CDD`) dereferences streamlist entries as raw
bank-0 addresses with **no range check and no forwarding**. Normally every
streamlist value comes from fixed ROM. The overrun lets you plant your own.

**The chain (simulation only):** a 20-address C9 payload where positions
15–19 are crafted to control the overrun's post-corruption state:

```
[0..14]  main_addr × 15      (any forwarded addr, safe lo byte)
[15]     $5E0F               (sets n=$10 after INC, cursor=$0E)
[16]     $5E0B               (repairs $07E3: lo=$0B, bits 0+1 set)
[17]     $5Xhh               (lo=target cs_payload offset for hi byte)
[18]     $5Xvv               (lo=stale c9_sub_value = streamlist hi byte)
[19]     $5Xll               (lo=target cs_payload offset for lo byte)
```

After the overrun, `$07E3` has both bits set (reply builder skips first-
frame setup), so the very first downstream frame writes the **stale**
`c9_sub_value` — the byte placed at `$07E7` by position 18's addr_store —
before any H8 reply arrives. This breaks the coupling between target offset
and H8 address that blocks the naive approach.

Frame 0 writes the stale byte (the streamlist hi byte) to `$07A1`. Frame 4
writes an H8 reply (the lo byte) to `$07A0`. Stop streaming after frame 4.

**Achievable hidden-region addresses:** 45–65 depending on H8 RAM state
(the lo byte depends on H8 reply values in the chain). Across four H8
dumps, 65 addresses covering all 6 hi-byte pages (`$5D`–`$62`) with 13
distinct lo bytes:

```
$00 $05 $18 $21 $25 $30 $80 $81 $86 $A0 $C1 $FB $FF
```

Using both streamlist entries (`$07A0/$07A1` and `$07A2/$07A3`) adds ~5
more. The H8 RAM is live data — different engine conditions produce
different values, potentially unlocking more lo bytes.

**To read a hidden byte:** fire the overrun (one C9 command + F0, stream 5
frames, stop), then re-init and fire `0A` direct mode. The direct-mode
reply builder reads from the planted address — on the main CPU, with no
forwarding to the H8. This is the main CPU's own code at `$5D40–$623F`
that C9 normally intercepts and forwards.

**What this would mean (if confirmed):** 50+ bytes scattered across the
1280-byte hidden region — enough to confirm whether it's code vs data, find
instruction patterns, and identify structure.

**Hardware result:** [hidden-read log](logs/2026-11-15_hidden-read.log),
20:46:52 — a 20-address plant targeted `$5E25`. Readback of `$07A0–$07A3`
returned `00 00 00 00`: the plant failed. A subsequent `0A 02 81` also
returned `$FE` instead of `$81`, suggesting persistent corruption or a
command-validity issue. Additionally, `0A` reloads streamlist entries from
ROM (`$525A`), overwriting any plant — a mixed 0A/C9 workaround was
proposed but never tested. Root cause of the model/hardware disagreement
is unresolved ([FINDINGS.md §hidden-code chain](docs/processor-write/FINDINGS.md)).

### 2. Set `at_active` flags (`$07B7–$07C2`)

**(Simulation only; hardware claim withdrawn.)**

The model predicts downstream writes can set bits in `at_active`. The
`c9_actuator_test.py` trials showed sustained `$02`/`$0B` in reply-payload
bytes during streaming, but those are output positions in the frame, not
independent readback of `$07B7`. The final review of the
[actuator log](logs/2026-11-15_c9-actuator.log) found no target-address
change in any of the nine sessions
([FINDINGS.md](docs/processor-write/FINDINGS.md)).

If the downstream write does reach these flags, the intended test
activations would be:

| Flag | Test | Effect |
|---|---|---|
| `$07B7.01` | `80` | Coolant temp override (bank 1 handler) |
| `$07B7.02` | `81` | Fuel injection — clamped 75–125 %, writes alpha `$0730` |
| `$07B7.04` | `82` | Ignition timing (bank 1 handler) |
| `$07B7.20` | `85` | IACV-AAC opening — forces register `18`, ≤ 129 steps |
| `$07B8.10` | `8C` | Forces an idle-air path (`$BC22`) |
| `$07B9.08` | `93` | Cooling fan low (bank 1 — relay driver is on the H8) |
| `$07B9.10` | `94` | Cooling fan high (bank 1) |
| `$07BA.01` | `98` | Purge volume control — forces register `29` |

### 3. Set `at_req` flags (`$07AC–$07B6`)

**(Simulation only.)**

The "request" flags that get copied to `at_active` on F0. Writing them
means the next normal Consult command cycle activates those tests without
ever sending `0A`. Note: `at_req` is in the `consult_reset` clear range,
so any write would be wiped by stop before post-stop readback.

### 4. Write `at_values` (`$076F–$079C`)

**(Simulation only — but the best candidate for hardware verification.)**

The value bytes that active-test handlers consume. `at_values` is NOT
cleared by `consult_reset`, so a successful write here persists through
stop and can be verified by independent post-stop readback — unlike the
`at_active`/`at_req` targets that were used in all previous trials.

Combined with setting the flag bits (#2/#3), this activates a test and
chooses its parameter through a path that bypasses `0A` input validation
entirely.

For bank-0 tests with known handlers: fuel injection percentage (`$0770`),
IACV step count (`$0774`), purge volume (`$0787`).

**Unexplored angle:** `0A` descriptors clamp some values (e.g. fuel
injection to `$4B–$7D`). Writing through the overrun skips the descriptor
lookup, so the handler sees whatever byte you placed. Whether the handler
re-clamps or trusts the value is worth checking in the disassembly.

### 5. Signal the H8 indirectly

**(Theoretical — depends on #2 working.)**

Any active-test flag sets `$07F1.2`, which is sent to the second CPU in
the outgoing message block. The H8 sees "an active test is running."
The relay drivers (fuel pump `89`, fans `93`/`94`) are in H8 code — the
flags might make it act, but you're flying blind without the H8 ROM.

### 6. Corrupt the reply builder state

**(Hardware-confirmed.)** The [overrun log](logs/2026-11-15_c9-overrun-test.log)
shows altered `$07E2` (cursor) and `$07E3` (flags) values in all four
sessions — the direct overrun demonstrably corrupts the reply builder's
control bytes. Setting the reply cursor and `c9_hidden_n` to arbitrary
values causes the reply builder to cycle through corrupted idx entries.
Each frame writes `c9_sub_value` to a different `cs_payload` offset.

### 7. Pre-load `cs_argbuf` (`$08D2`)

**(Simulation only.)**

The argument buffer for the next Consult command. You could pre-load C9
addresses that a subsequent normal command would read, though this is more
strange than useful.

## What does not work

- **Read the H8's program ROM.** The forward window covers `$0D40–$123F`
  only — data/scratch RAM, not code.
- **Execute code.** No RAM function pointer exists to hijack (ROM_ANALYSIS.md
  §10). The only indirect jump, `JMP ($CBAB,X)` at `$CAF1`, uses a fixed
  9-entry ROM table, X bounded 0–8 by the search loop.
- **Write outside `$0740–$08D6`.** Both index masks are `& $FF`; the base
  addresses (`$07C3` for addr, `$07D7` for idx, `$0740` for downstream)
  anchor the window.
- **Control c9_sub_value across multiple frames.** The overrun (position 18)
  or the stale-write trick (§1) sets `c9_sub_value` for the first frame.
  Later frames depend on H8 replies, so only the first downstream write
  after the overrun carries the chosen byte.
- **Reach bank 1.** Data bank register is hardcoded to 0 (`$3D80`, `$4486`),
  never changed. No long-indirect read exists in the ROM.
- **Fire parameter tests safely with engine running.** `81` (injection),
  `82` (timing), `85` (IACV) have real effects on the running engine.

## Timing concern

The downstream write depends on `consult_reply_c9` reading the overrun's
pre-loaded `c9_sub_value` before anything else overwrites it. The
disassembly shows two hazards the simulation does not model:

**1. Mailbox handshake gate (`$9B2F`).**

The builder's entry sequence (disassembly lines at `$9B2A–$9B3D`):

```
$9B2A  BBC $07E3,#$01,L_9B89   ; bit 0 clear → skip hidden processing
$9B2F  BBS $029E,#$10,L_9B89   ; mb_handshake bit 4 SET → skip (mailbox busy)
$9B34  BBS $07E3,#$02,L_9B3F   ; bit 1 set → proceed to builder
$9B39  SEB $07E3,#$02           ; first frame: set bit 1, then skip write
$9B3D  BRA L_9B6A
```

The overrun sets `$07E3 = $0B` (bits 0, 1, 3), so bit 0 passes and bit 1
passes (jump to `$9B3F`). But if `$029E` bit 4 is set when the first
frame runs, the builder skips entirely — the pre-loaded value is never
read. Whether the mailbox is busy at that instant depends on the H8
response timing, which the simulation does not model.

**2. Mailbox receive overwrites `$07E7` (`$C862`).**

```
$C860  LDA $16,X               ; X = $02A0 (&mb_in)
$C862  STA $07E7               ; c9_sub_value ← H8 response byte
```

`mailbox_receive` copies the H8's response into `c9_sub_value`. The
overrun pre-loads `$07E7` during `c9_find_hidden` (which runs at F0
processing time). The builder reads `$07E7` during the streaming loop.
If `mailbox_receive` executes in between — e.g. because the H8 responds
to the forwarded addresses — the pre-loaded value is destroyed.

**Why this matters:** the overrun itself is hardware-confirmed (the direct
stores demonstrably corrupt `$07E1–$07E5` and redirect the index store to
`$0817`). The open question is whether the downstream store at `$9B5E`
fires with the intended value and index. Every previous hardware trial
that targeted downstream addresses (`at_active`, `cs_streamlist`) showed
no target-address change. The timing hazards above are the most likely
explanation, though a simulation error is also possible.

**Next step:** write to `at_values` (`$076F–$079C`) using `c9_write.py`,
which survives `consult_reset` and can be verified by independent post-stop
readback. A confirmed value change there would prove the downstream path
works; a failure would isolate the timing hazard.
