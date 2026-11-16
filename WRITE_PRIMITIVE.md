# Write primitive: what it can do

> **Evidence update (2026-11-15):** See [processor-write findings](docs/processor-write/FINDINGS.md) and the [preserved logs and sessions](docs/processor-write/SESSIONS.md). The overrun is observed, but the latest hardware streamlist plant failed, and Claude’s final review withdrew earlier actuator-target success claims. Hidden-read success and the stale-value chain remain unconfirmed. Earlier absolute conclusions below are historical and may be superseded.

Summary of capabilities and limits of the `c9_find_hidden` buffer overrun
(ROM_ANALYSIS.md §10) on the 23710-2L904 engine ECU.

## The primitive

Send 16–20 C9 addresses all inside `$5D40–$623F`, then `F0`. The ECU's
`c9_hidden_addr` and `c9_hidden_idx` arrays hold 10 entries each, but the
loop has no upper-bound check — it runs to `cs_argc` (up to 20). From
`i = 10` the stores walk off the end into live handler state.

Two stages:

1. **Direct overrun** (`c9_find_hidden`, `$543F`): at `i = 15` the 16-bit
   addr store writes attacker-controlled data into `c9_hidden_n` (`$07E1`)
   and the reply cursor (`$07E2`). The 18-address payload in
   `c9_actuator_test.py` includes a repair sequence (positions 15–17) that
   fixes `$07E3` bit 0 so the reply builder still runs.

2. **Downstream OOB** (`consult_reply_c9`, `$9B3F`): corrupted
   `c9_hidden_idx[]` entries cause the per-frame write
   `cs_payload[idx] = c9_sub_value` to escape the 40-byte payload buffer,
   reaching `$0740–$083F`.

## Constraints

| Constraint | Detail |
|---|---|
| Destination range | `$0740–$08D6` (~275 bytes) via the direct overrun; `$0740–$083F` (256 bytes) via the downstream write |
| Value range (direct) | 16-bit word in `$0D40–$123F` (low byte free, high byte pinned `$0D–$12`), or the loop counter (0–19) |
| Value range (downstream) | One byte: whatever `c9_sub_value` (`$07E7`) holds — the H8's last reply, not directly caller-controlled |
| Persistence | Survives re-init. Only a key cycle clears it |
| Code execution | Impossible — no RAM function pointer exists anywhere in the image (ROM_ANALYSIS.md §10) |

## What works

### 1. Write to `cs_streamlist` + read hidden code (`$5D40–$623F`)

The ROM analysis (§11) flagged `cs_streamlist` as unreachable from Consult.
The overrun's downstream OOB *can* reach it — and chains with the
`consult_reply_direct` read bug to read the main CPU's hidden code.

`consult_reply_direct` (`$9CDD`) dereferences streamlist entries as raw
bank-0 addresses with **no range check and no forwarding**. Normally every
streamlist value comes from fixed ROM. The overrun lets you plant your own.

**The chain (confirmed by simulation):** a 20-address C9 payload where
positions 15–19 are crafted to control the overrun's post-corruption state:

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

**What this means:** 50+ bytes scattered across the 1280-byte hidden region.
Enough to confirm whether it's code vs data, find instruction patterns, and
identify structure — a foothold for mapping the hidden code without
desoldering the H8.

### 2. Set `at_active` flags (`$07B7–$07C2`)

Confirmed by `c9_actuator_test.py` — sustained `$02`/`$0B` visible during
streaming. Writing bits into the active-test flag bytes activates tests.
Bank-0 handlers that respond:

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

The "request" flags that get copied to `at_active` on F0. Writing them
means the next normal Consult command cycle activates those tests without
ever sending `0A`.

### 4. Write `at_values` (`$076F–$079C`)

The value bytes that active-test handlers consume. Combined with setting
the flag bits (#2/#3), this activates a test and chooses its parameter
through a path that bypasses `0A` input validation entirely.

For bank-0 tests with known handlers: fuel injection percentage (`$0770`),
IACV step count (`$0774`), purge volume (`$0787`).

**Unexplored angle:** `0A` descriptors clamp some values (e.g. fuel
injection to `$4B–$7D`). Writing through the overrun skips the descriptor
lookup, so the handler sees whatever byte you placed. Whether the handler
re-clamps or trusts the value is worth checking in the disassembly.

### 5. Signal the H8 indirectly

Any active-test flag sets `$07F1.2`, which is sent to the second CPU in
the outgoing message block. The H8 sees "an active test is running."
The relay drivers (fuel pump `89`, fans `93`/`94`) are in H8 code — the
flags might make it act, but you're flying blind without the H8 ROM.

### 6. Corrupt the reply builder state

Setting the reply cursor and `c9_hidden_n` to arbitrary values causes the
reply builder to cycle through corrupted idx entries. Each frame writes
`c9_sub_value` to a different `cs_payload` offset. This is the mechanism
`c9_actuator_test.py` already uses.

### 7. Pre-load `cs_argbuf` (`$08D2`)

The argument buffer for the next Consult command. You could pre-load C9
addresses that a subsequent normal command would read, though this is more
strange than useful.

## What does not work

- **Read the H8's program ROM.** The forward window covers `$0D40–$123F`
  only — data/scratch RAM, not code.
- **Execute code.** No RAM function pointer exists to hijack. The only
  indirect jump (`$CAF1`) uses a fixed 9-entry ROM table, X bounded 0–8.
- **Write outside `$0740–$08D6`.** Both index masks are `& $FF`; the base
  addresses (`$07C3` for addr, `$07D7` for idx, `$0740` for downstream)
  anchor the window.
- **Control the downstream write's value directly.** It's `c9_sub_value`,
  but the stale-write trick (§1 above) partially breaks this: the first
  frame's value is chosen by the overrun, not the H8. Later frames still
  depend on H8 replies.
- **Reach bank 1.** Data bank register is hardcoded to 0 (`$3D80`, `$4486`),
  never changed. No long-indirect read exists in the ROM.
- **Fire parameter tests safely with engine running.** `81` (injection),
  `82` (timing), `85` (IACV) have real effects on the running engine.
