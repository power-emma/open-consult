# Write primitive: what it can do

> **RELIABLE WRITE ACHIEVED (2026-11-16):** 25/25 confirmed writes.
> `tools/c9_write_primed.py --taps 2` writes $93 to any address in
> $0740–$083F.  Double-tap (1 frame each), fire fast after key-on.
> Write is real: persists across 10+ init/read/stop cycles.
>
> **Value = $93 (not yet controllable).**  The H8 FIFO always yields $93
> at drain position 2+ regardless of fill address (20/20 sweep) or tap
> count (taps 3–10 all $93).  Engine running gives live sensor data
> ($99–$9B) instead.  Arbitrary value control is the remaining gap.
>
> **Mechanism:** the builder at `L_9B3F` writes `$07E7` to the target on
> every frame.  Multi-frame overruns self-clobber; 1-frame overruns
> preserve frame 0's value.  Tap 1 primes the FIFO past $00; tap 2's
> frame 0 catches $93.
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
   payload buffer into `$0740–$083F`. **Hardware-confirmed** by
   `c9_write_framehit.py` (2026-11-16): targeting `cs_payload[0]` changed
   `frame[0]` from `$20` to `$00`.  The written value is the H8 response
   for position 18, not the pre-loaded byte (see [timing](#timing-resolved)).

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

**Timing resolved:** the builder gate at `$9B2F` does not block in
practice.  `mailbox_receive` at `$C862` does overwrite `$07E7` with the
H8's response — this is confirmed and is now the value-control mechanism.
The written value = H8 response for position 18.  See [timing](#timing-resolved).

## Constraints

| Constraint | Detail |
|---|---|
| Destination range | `$0740–$08D6` (~275 bytes) via the direct overrun; `$0740–$083F` (256 bytes, arbitrary byte) via the downstream write |
| Value range (direct) | 16-bit word in `$0D40–$123F` (low byte free, high byte pinned `$0D–$12`), or the loop counter (0–19) |
| Value range (downstream) | $93 at key-on/engine-off (deterministic, 25/25); $99–$9B with engine running (live H8 data, fluctuates); arbitrary value control not yet achieved |
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
- **Choose an arbitrary write value.**  The H8 FIFO sequence is fixed at
  $00, $00, $93, $93... for key-on/engine-off.  Fill addresses and tap
  counts do not change it.  The only variation observed is engine-running
  live data ($99–$9B), which is not controllable.
- **Reach bank 1.** Data bank register is hardcoded to 0 (`$3D80`, `$4486`),
  never changed. No long-indirect read exists in the ROM.
- **Fire parameter tests safely with engine running.** `81` (injection),
  `82` (timing), `85` (IACV) have real effects on the running engine.

## Timing: resolved

The downstream write was confirmed on hardware by `c9_write_framehit.py`
(2026-11-16).  The builder at `$9B5E` fires.  The two timing hazards
identified earlier have known outcomes:

**1. Mailbox handshake gate (`$9B2F`):** does NOT block the builder on
the first frame in practice.  The gate checks `$029E` bit 4 (mailbox
busy); empirically the mailbox is not busy when the first frame runs.

**2. Mailbox receive clobbers `$07E7` (`$C862`):** CONFIRMED.  This is
not a hazard — it's the mechanism.  `mailbox_receive` always runs before
the builder reads `c9_sub_value`, replacing the overrun's pre-loaded byte
with an H8 response from the FIFO.

**Key finding (2026-11-16):** position 18's forwarded address is
irrelevant in streaming context — `frame[18]` H8 response is always
`$00` regardless of address.  The H8 serves from an internal sequential
FIFO that ignores the requested address.  The actual write value comes
from the overrun-phase FIFO: the 19 H8 requests queued by
`c9_find_hidden` drain asynchronously, and the last response in `$07E7`
when the builder reads it determines the write value.  The FIFO content
depends on the **fill addresses** (positions 0-14).  H8 data depletes
after the first streaming session per key cycle.

**Previous "no change" results explained:** the H8 FIFO value happened
to equal the existing RAM content, making the write invisible.  The write
was always firing; the value was just not controlled.

**Value control strategy:** vary the fill addresses across different H8
record bases ("spread fill") to change the FIFO content.  Characterize
empirically with `tools/c9_write_fifo.py`.  `tools/h8_sweep.py` is
valid for one-shot reads only, not streaming.

## Reliable write achieved (2026-11-16): double-tap, single frame

**25/25 confirmed writes across all tests.**
`tools/c9_write_primed.py --taps 2` writes $93 to any address in
$0740–$083F deterministically.  The write is real, persistent within a
key cycle, and independently verified by repeated readback.

### Key findings

1. **Builder rewrites on every frame.**  `L_9B3F` writes `$07E7` to the
   target on each streaming frame.  With 3 frames, frame 0's value gets
   clobbered by frames 1–2.  Fix: stream exactly 1 frame per tap.

2. **Double-tap required.**  Tap 1 (primer) advances the H8 FIFO past
   its initial $00 entries.  Tap 2 catches $93 from the FIFO.  Single
   tap writes $00 (unreliable) or $93 depending on timing.

3. **Timing window.**  Must fire quickly after key-on.  Waiting 6+
   seconds causes the H8 state to advance past the useful FIFO position;
   the write value becomes $00.

4. **Write is real and sticky.**  After writing $93 to $0817, 10
   consecutive init/read/stop cycles all returned $93.  The value
   persists across re-init and stop — it's physically stored in RAM,
   not FIFO passthrough.

5. **Fill address doesn't matter.**  20 different fill addresses ($5D40
   through $6200 at $40 stride), all produced $93.  The FIFO drain
   position is structural (determined by the tap sequence), not by
   which H8 records positions 0–14 point to.

6. **Tap count doesn't matter either.**  Sweeping taps 1–10: taps 1–2
   write $00, tap 3+ all write $93.  The FIFO sequence is
   $00, $00, $93, $93, $93...  — once $93 arrives it stays.  There is
   no FIFO position that yields $00 (or any other value) after $93.

7. **Engine running gives live H8 values.**  With engine on (no key
   cycles between trials), the written values were $99–$9B — live
   sensor data from the H8 that fluctuates with engine conditions.
   Writes were confirmed real by persistence across readbacks.

8. **Probe reads before builder writes.**  Position 19 (target address)
   in the frame always shows the pre-write value.  The builder processes
   hidden addresses after building frame data for position 19.  Only
   post-stop readback shows the actual written value.

### Results

**Reliability (5/5, engine off, key cycle between each):**
```
Trial  Baseline  Readback
1      $00       $93
2      $00       $93
3      $00       $93
4      $00       $93
5      $00       $93
```

**Persistence (10/10 readbacks after one write):**
```
$93 $93 $93 $93 $93 $93 $93 $93 $93 $93
```

**Fill sweep (20/20, all $93):**
```
$5D40 $5D80 $5DC0 $5E00 $5E40 $5E80 $5EC0 $5F00 $5F40 $5F80
$5FC0 $6000 $6040 $6080 $60C0 $6100 $6140 $6180 $61C0 $6200
```

**Tap sweep (taps=6 example):**
```
Tap 1: probe=$00  (writes $00 — throwaway)
Tap 2: probe=$00  (writes $93 — but probe reads pre-write)
Tap 3: probe=$93  (writes $93 — probe sees tap 2's write)
Tap 4: probe=$93
Tap 5: probe=$93
Tap 6: probe=$93
Readback: $93
```

### Value control status

**$93 is the only achievable value at key-on / engine-off.**  The H8
FIFO sequence is fixed: $00, $00, $93, $93, $93...  Fill addresses and
tap count do not change it.  $93 appears to be whatever H8 register
the FIFO happens to serve at drain position 2+.

**With engine running**, live H8 sensor data ($99–$9B observed) replaces
$93, fluctuating with engine conditions.  Different conditions may yield
different values, but this is not controlled — it's whatever the H8 is
measuring at that moment.

**Remaining paths to arbitrary value control:**
- **Multi-frame taps:** stream 2+ frames per tap to land at different
  sub-positions within each FIFO drain cycle (not yet tested).
- **Spread fill:** different addresses at each of positions 0–14
  (not uniform fill) to change the FIFO's internal interleaving.
- **Engine conditions:** engine running at different RPM/temp to shift
  the H8's live data into a desired range.
- **Different target address:** the target offset feeds into idx_store,
  which may shift the FIFO alignment (not yet tested).

### Practical applications with $93

Even without arbitrary value control, $93 enables:

| Application | How | Notes |
|---|---|---|
| **Prove write to any address** | Write $93, readback | Confirmed for $0817 |
| **Set at_active flags** | Write $93 to $07B7–$07C2 | $93 = bits 0,1,4,7 set; activates tests 80,84,87 on bank 1 |
| **Plant at_values** | Write $93 to $076F–$079C | Unclamped parameter: $93 = 147 decimal |
| **Corrupt DTC state** | Write $93 to $0810–$083F | Plants non-zero DTC data |
| **Probe builder behavior** | Write to cs_payload | Observe frame corruption patterns |

As demonstrated, it can change a byte in the ECU’s working RAM through the diagnostic connection, with the change surviving diagnostic stop and reinitialization. A key cycle reportedly clears it.

Its potential depends on which RAM byte it reaches:

| Target | Possible effect | Evidence |
|---|---|---|
| $0817 | Change a byte labeled diagnostic trouble-code bookkeeping | Repeated write/readback demonstrated; functional effect untested |
| Active-test flags | Enable diagnostic overrides affecting injection, timing, idle air, or fans | Proposed; successful actuator control unproven |
| Active-test parameters | Alter the values those overrides consume | Proposed; needs destination and value-control verification |
| Stream pointers | Redirect diagnostic reads, potentially exposing otherwise hidden main-CPU bytes | Earlier attempt failed |
| Diagnostic handler state | Corrupt replies or disrupt the diagnostic session | Recorded corruption supports this |

The biggest limitation is value control: repeatedly writing $93 gives much less control than choosing any byte. $93 could still matter at a flag byte because it sets several bits, but neighboring state, reset behavior, and handler checks determine the actual effect.

### Bounds


| Result | Addresses |
|---|---|
| Changed to $93 | $0740, $07AB, $07C3, $07C4, $07C8, $07CF, $07D0, $07E0, $083F |
| No lasting change observed | $07AC, $07AD, $07AF, $07C0, $07C2 |
| Outside this method’s range | $0840 and above; below $0740 |


### Summary

So its established capability is persistent-within-a-key-cycle RAM corruption. Engine-control manipulation is a plausible consequence to investigate, but the folder does not yet prove it. There’s also no demonstrated firmware flashing, permanent modification, or code execution.

### Tools

```
python3 tools/c9_write_primed.py --target 0817              # double-tap write
python3 tools/c9_write_primed.py --target 0817 --repeat 5   # reliability test
python3 tools/c9_write_primed.py --target 0817 --taps 1     # single tap (writes $00)
python3 tools/c9_write_primed.py --target 0817 --taps 6     # multi-tap (still $93)
python3 tools/c9_write_fillsweep.py --target 0817           # fill address sweep
python3 tools/c9_write_tapsweep.py --taps 1,2,3,4,5,6       # tap count sweep
python3 tools/c9_readback.py --target 0817 -n 10            # persistence check
```
