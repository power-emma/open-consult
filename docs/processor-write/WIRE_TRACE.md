# Wire trace: writing $A5 to $076F

Every byte on the wire for `c9_write_test.py` Trial 1, and why each one
is that value.  9600 8N1, half-duplex, Consult-I protocol.

Target ECU: 23710-2L904 (1998 Maxima VQ30DE, M37732 main processor).

## How to read this

**TX** = host sends.  **RX** = ECU replies.  All values hex.
The ECU is a passive responder — it never sends unsolicited data.
Every TX byte is a deliberate choice by the host; every RX byte is the
ECU's deterministic response to the state those TX bytes created.

## 1. Init

Establish the Consult-I session.

```
TX: FF          wait 280 ms
TX: FF          wait 70 ms
TX: ED          ECU selector (engine, 1998 Maxima)
RX: 12          ~ED & FF = $12 (init ack)
```

Timing gaps match ECUTalk 1.5.0 (decompiled).  The ECU answers ED
specifically; it ignores the standard EF.  If no `12` comes back within
2 seconds, retry (up to 5 attempts).

## 2. Baseline read

Read the target byte before the write, so we can tell if it changed.

```
TX: C9 07 6F    C9 command: read one byte at $076F
RX: 36 07 6F    echo: ~C9=36, then addr bytes verbatim

TX: F0          GO — start streaming
RX: FF 01 xx    frame: FF sync, 01 = 1 byte payload, xx = value at $076F
TX: 30          STOP
RX: CF          stop ack (or FE)
```

The `xx` is the baseline.  For a fresh key-on it's typically `$00`.

## 3. Re-init

Re-establish the session (stop drops it).

```
TX: FF ... FF ... ED
RX: 12
```

Same as step 1.

## 4. The write command (60 bytes)

Twenty C9 address reads sent as a single burst.  Each is 3 bytes:
`C9` (command), then the 16-bit address high/low.

```
TX: C9 5E 00    pos  0: $5E00   ─┐
TX: C9 5E 00    pos  1: $5E00    │
TX: C9 5E 00    pos  2: $5E00    │
TX: C9 5E 00    pos  3: $5E00    │
TX: C9 5E 00    pos  4: $5E00    │  15 identical fill addresses.
TX: C9 5E 00    pos  5: $5E00    │  $5E00 is in the forwarded range
TX: C9 5E 00    pos  6: $5E00    │  ($5D40-$623F), so each one
TX: C9 5E 00    pos  7: $5E00    │  increments the hidden-address
TX: C9 5E 00    pos  8: $5E00    │  counter.  The low byte ($00)
TX: C9 5E 00    pos  9: $5E00    │  doesn't matter for the fill.
TX: C9 5E 00    pos 10: $5E00    │
TX: C9 5E 00    pos 11: $5E00    │
TX: C9 5E 00    pos 12: $5E00    │
TX: C9 5E 00    pos 13: $5E00    │
TX: C9 5E 00    pos 14: $5E00   ─┘
TX: C9 5E 0A    pos 15: $5E0A   repair_a  (see §5)
TX: C9 5E 0B    pos 16: $5E0B   repair_b  (see §5)
TX: C9 5E 2F    pos 17: $5E2F   target    (see §5)
TX: C9 5E A5    pos 18: $5EA5   value     (see §5)
TX: C9 07 6F    pos 19: $076F   probe     (see §5)
```

The ECU echoes each command as `~C9` ($36) + addr bytes:

```
RX: 36 5E 00    echo of pos  0
RX: 36 5E 00    echo of pos  1
 ...             (13 more identical echoes)
RX: 36 5E 0A    echo of pos 15
RX: 36 5E 0B    echo of pos 16
RX: 36 5E 2F    echo of pos 17
RX: 36 5E A5    echo of pos 18
RX: 36 07 6F    echo of pos 19
```

Total: 60 TX bytes, 60 RX echo bytes.  After the echo is verified:

```
TX: F0          GO — start streaming
```

F0 triggers two things: `c9_find_hidden` ($543F) processes the queued
addresses (the overrun happens here), then the streaming loop begins
(the downstream write happens on the first frame).

**Argument budget:** 20 addresses x 2 argument bytes = 40 bytes, which
is exactly the `cs_argbuf` limit.  21 addresses would be rejected.

## 5. Why those specific bytes

### What the hidden-address mechanism is for

When a C9 request includes addresses in the $5D40-$623F range, the main
CPU can't read them locally — that range is forwarded to the H8 second
processor, which returns one byte per frame through the shared mailbox.
So the ECU needs to remember which addresses were forwarded and which
position in the reply each one corresponds to, in order to slot the H8's
answers into the right frame bytes as they arrive.

`c9_find_hidden` ($543F) builds this bookkeeping.  It scans every
queued C9 address and, for each forwarded one, appends two things:

- `c9_hidden_addr` ($07C3): the forwarded address (for the H8 request)
- `c9_hidden_idx` ($07D7): which position in the reply this address
  occupies (so the builder knows where to put the H8's answer)

`c9_hidden_n` ($07E1) is the count — how many forwarded addresses were
found.  It starts at 0 and increments after each append.  It's also the
array index for the next store: entry n goes to $07C3 + 2*n (addr) and
$07D7 + n (idx).

In normal use (1-10 forwarded addresses), this is just bookkeeping.
The arrays hold 10 entries, n stays in 0-10, and everything is fine.

### The overrun

The loop terminator at $54C0 checks the argument byte count (`cs_argc`),
not the array capacity.  With 20 forwarded addresses, `cs_argc` = 40 and
the loop runs 20 iterations.  From i=10 onward, n=10+ and the stores
walk off the end of both arrays into the handler state bytes that
immediately follow them in RAM:

```
$07C3-$07D6   c9_hidden_addr[0..9]   (10 entries x 2 bytes)
$07D7-$07E0   c9_hidden_idx[0..9]    (10 entries x 1 byte)
$07E1         c9_hidden_n            ← overrun starts hitting here at i=10
$07E2         reply_cursor
$07E3         fwd_flags
$07E4-$07E6   (forward state)
$07E7         c9_sub_value           (the byte the builder writes)
```

The store formulas don't change — the ROM has no idea it's overrunning:

```
addr_store ($54A0):  [$07C3 + 2*n] <- (address - $5000)    16-bit
idx_store  ($54B2):  [$07D7 + n]   <- i                     8-bit
                     n = n + 1                               INC $07E1
```

The destinations aren't chosen — they're computed by the same formula
the ROM always uses, operating past its intended bounds.

### Iteration-by-iteration

| i | n | addr_store dest | addr_store value | idx_store dest | idx_store value | what happened |
|---|---|---|---|---|---|---|
| 0 | $00 | $07C3 | $0E00 | $07D7 | $00 | normal: hidden_addr[0], hidden_idx[0] |
| 1 | $01 | $07C5 | $0E00 | $07D8 | $01 | normal |
| 2 | $02 | $07C7 | $0E00 | $07D9 | $02 | normal |
| 3 | $03 | $07C9 | $0E00 | $07DA | $03 | normal |
| 4 | $04 | $07CB | $0E00 | $07DB | $04 | normal |
| 5 | $05 | $07CD | $0E00 | $07DC | $05 | normal |
| 6 | $06 | $07CF | $0E00 | $07DD | $06 | normal |
| 7 | $07 | $07D1 | $0E00 | $07DE | $07 | normal |
| 8 | $08 | $07D3 | $0E00 | $07DF | $08 | normal |
| 9 | $09 | $07D5 | $0E00 | $07E0 | $09 | normal — last in-bounds |
| 10 | $0A | $07D7 | $0E00 | **$07E1** | $0A | **overrun**: idx store hits c9_hidden_n |
| 11 | $0B | $07D9 | $0E00 | **$07E2** | $0B | idx store hits reply_cursor |
| 12 | $0C | $07DB | $0E00 | **$07E3** | $0C | idx store hits fwd_flags |
| 13 | $0D | $07DD | $0E00 | $07E4 | $0D | |
| 14 | $0E | $07DF | $0E00 | **$07E5** | $0E | idx store hits idx[$0E] |

Iterations 10-14 scribble loop counters ($0A-$0E) over handler state.
This is damage, not control.  Control starts at i=15.

### Position 15 — the pivot ($5E0A)

```
addr_store: dest = $07C3 + 2*$0F = $07E1
            value = $5E0A - $5000 = $0E0A  (16-bit)
            $07E1 (lo) <- $0A     c9_hidden_n = $0A
            $07E2 (hi) <- $0E     reply_cursor = $0E

idx_store:  dest = $07D7 + $0A = $07E1   (re-reads the just-set n=$0A)
            $07E1 <- $0F  (i=15)
            INC $07E1 -> $10
```

This is the critical iteration.  It's the first time the addr store
reaches $07E1 — `c9_hidden_n` itself — because n=$0F makes the
destination $07C3 + 2*$0F = $07E1.  That variable is the one the loop
uses to compute where every store lands.  The overrun is writing to the
thing that controls where subsequent overwrites go.

Before i=15, the damage from i=10-14 is uncontrolled.  The idx store
walks linearly through $07E1, $07E2, $07E3, ..., depositing the loop
counters 10-14.  That clobbers c9_hidden_n, reply_cursor, and fwd_flags
with whatever the counter happens to be.  There's no choice in it.

At i=15, the addr store is 16-bit, and the word it writes is
`address - $5000`.  The forwarded range ($5D40-$623F) means the high
byte is pinned ($0D-$12), but the low byte is free — it's whatever you
put in the address.  We send $5E0A:

- Low byte $0A goes to $07E1 (c9_hidden_n)
- High byte $0E goes to $07E2 (reply_cursor)

Then, in the same iteration, the idx store re-reads $07E1 to compute
its own destination ($07D7 + n).  It reads the $0A we just wrote, so it
stores to $07D7 + $0A = $07E1 — writing the loop counter (15 = $0F)
back into c9_hidden_n.  Then INC bumps it to $10.

After i=15, n = $10.  That determines every subsequent addr store
destination via the formula $07C3 + 2*n:

```
i=16: n=$10 → $07C3 + $20 = $07E3   fwd_flags     (position 16 writes here)
i=17: n=$11 → $07C3 + $22 = $07E5   idx[$0E]      (position 17 writes here)
i=18: n=$12 → $07C3 + $24 = $07E7   c9_sub_value  (position 18 writes here)
```

Those three addresses are exactly the three handler variables the
builder reads to decide what byte to write and where.  That's not a
coincidence — the low byte $0A was chosen by working backward: we need
n=$10 after the INC so that the remaining iterations hit $07E3, $07E5,
$07E7 in order.  $10 - 1 = $0F (what INC starts from), and the idx
store writes the loop counter (15 = $0F) to $07E1 only if it re-reads
n=$0A from $07E1, which means the addr store's low byte must be $0A.

A different low byte breaks the chain.  For example, $5E08 would leave
n=$0E after INC, making i=16 hit $07DF instead of $07E3 — wrong
target, wrong result.

### Position 16 — repair flags ($5E0B)

```
addr_store: dest = $07C3 + 2*$10 = $07E3
            value = $5E0B - $5000 = $0E0B  (16-bit)
            $07E3 (lo) <- $0B     fwd_flags: bits 0 + 1 + 3 SET

idx_store:  dest = $07D7 + $10 = $07E7
            $07E7 <- $10  (i=16)    c9_sub_value = $10
            INC $07E1 -> $11
```

**Why $5E0B:** the low byte $0B = `0000_1011` sets bits 0 and 1 of
fwd_flags ($07E3).  The reply builder at $9B2A checks bit 0 (skip if
clear) and at $9B34 checks bit 1 (enter the write path if set).  Without
this repair, the builder skips the write entirely.  The idx store sets
c9_sub_value to $10 — this is a temporary value overwritten by position
18.

### Position 17 — set the target index ($5E2F)

```
addr_store: dest = $07C3 + 2*$11 = $07E5
            value = $5E2F - $5000 = $0E2F  (16-bit)
            $07E5 (lo) <- $2F     idx[$0E] = target offset

idx_store:  dest = $07D7 + $11 = $07E8
            $07E8 <- $11          (no critical effect)
            INC $07E1 -> $12
```

**Why $5E2F:** the low byte $2F is `$076F - $0740`.  It lands in $07E5,
which is `c9_hidden_idx[$0E]` (idx at the cursor position $0E set by
position 15).  The builder reads `idx[cursor]` and adds $0740 to get the
write destination.  So $2F + $0740 = $076F — our target.

**For any target T:** use address $5E00 + (T - $0740).

### Position 18 — set the value ($5EA5)

```
addr_store: dest = $07C3 + 2*$12 = $07E7
            value = $5EA5 - $5000 = $0EA5  (16-bit)
            $07E7 (lo) <- $A5     c9_sub_value = $A5 (!)

idx_store:  dest = $07D7 + $12 = $07E9
            $07E9 <- $12          (no critical effect)
            INC $07E1 -> $13
```

**Why $5EA5:** the low byte $A5 lands directly in c9_sub_value ($07E7).
The builder reads this byte and writes it to the target.  This is the
key advance: position 18's addr_store destination is mechanically
$07E7 because n=$12 after position 17, and $07C3 + 2*$12 = $07E7.
The desired byte rides in the low byte of the forwarded address.

**For any value V:** use address $5E00 + V.

### Position 19 — the probe ($076F)

$076F is NOT in the forwarded range ($5D40-$623F).  The overrun loop
checks this and breaks (it's the last iteration anyway).  No stores
happen.  But the reply builder still includes this address in the frame
response as a normal bank-0 RAM read — so each frame's byte [19] is the
live value at $076F.  This is how we watch the write take effect without
adding a 21st address.

### Summary: the parametric form

For any target `T` ($0740-$083F) and value `V` ($00-$FF):

```
pos  0-14:  $5E00               (fill)
pos 15:     $5E0A               (repair n + cursor)
pos 16:     $5E0B               (repair flags)
pos 17:     $5E00 + (T - $0740) (target index)
pos 18:     $5E00 + V           (value)
pos 19:     T                   (probe, not forwarded)
```

Only bytes 52-59 of the 60-byte command change between writes.

## 6. The downstream write

After F0, the ECU enters the streaming loop.  Each frame,
`consult_reply_c9` ($9B3F) runs.  On the first frame after the overrun:

### Gate sequence ($9B2A-$9B3D)

```
$9B2A  BBC $07E3,#$01,L_9B89    bit 0 of flags — clear means skip.
                                 Overrun set it to 1.  Pass.

$9B2F  BBS $029E,#$10,L_9B89    mailbox handshake bit 4 — set means
                                 the H8 is mid-reply.  Skip if busy.
                                 *** TIMING DEPENDENT — NOT MODELED ***

$9B34  BBS $07E3,#$02,L_9B3F    bit 1 of flags — set means not the
                                 first frame (skip setup).  Overrun
                                 set it to 1.  Jump to builder.
```

If $029E bit 4 happens to be set (mailbox busy), the builder skips
entirely and the write does not fire on this frame.

### Builder ($9B3F-$9B5E)

```
$9B3F  LDB $07E7           B = $A5         c9_sub_value (set by pos 18)
$9B47  LDA $07E2           A = $0E         reply_cursor (set by pos 15)
$9B4F  ADC #$07D7          X = $07E5       &idx[cursor]
$9B53  LDA $00,X           A = $2F         idx[$0E] (set by pos 17)
$9B59  ADC #$0740          X = $076F       &cs_payload[$2F] = target
$9B5E  STB $00,X           [$076F] <- $A5  THE WRITE
```

Every value the builder reads was placed by the overrun.  The builder
has no idea it's writing outside cs_payload ($0740-$0767) — it's using
the same code path it always uses, with corrupted inputs.

### Timing hazard: mailbox receive ($C862)

```
$C860  LDA $16,X           X = $02A0 (&mb_in)
$C862  STA $07E7           c9_sub_value <- H8 response byte
```

`mailbox_receive` copies the H8's latest response into $07E7.  The
overrun pre-loads $07E7 during F0 processing.  The builder reads it
during the streaming loop.  If `mailbox_receive` runs between those
two events, the pre-loaded $A5 is replaced with whatever the H8 sent.

This is the primary suspect for the model/hardware disagreement in all
previous downstream write attempts.

## 7. Frame response

Each frame is `FF` + length + payload:

```
RX: FF                  sync byte
RX: 14                  payload length = 20 ($14) bytes
RX: xx xx xx xx xx      bytes 0-4:   H8 forward data for $5E00 reads
RX: xx xx xx xx xx      bytes 5-9:   (same)
RX: xx xx xx xx xx      bytes 10-14: (same)
RX: xx                  byte 15:     H8 data for $5E0A
RX: xx                  byte 16:     H8 data for $5E0B
RX: xx                  byte 17:     H8 data for $5E2F
RX: xx                  byte 18:     H8 data for $5EA5
RX: xx                  byte 19:     PROBE — live RAM at $076F
```

Byte [19] is the one that matters.  The per-frame builder has two
phases, and the ROM runs them in this order:

**Phase 1 — address loop ($9AF1-$9B26):** iterates all 20 positions and
fills cs_payload (the frame buffer at $0740).  For non-forwarded
addresses like $076F, it reads RAM and stores the result:

```
$9B14  LDA $00,X         read RAM[$076F]  → old value
$9B16  STA $0000,Y       store to cs_payload[19] = $0753
```

At this point, the frame buffer byte for position 19 is filled with
the OLD value.  The hidden handler hasn't run yet.

**Phase 2 — hidden handler ($9B28-$9B5E):** runs AFTER the loop exits.
Writes c9_sub_value to cs_payload[idx], which with the corrupted index
goes to $0740 + $2F = $076F:

```
$9B3F  LDB $07E7         load c9_sub_value = $A5
$9B5E  STB $00,X         store to RAM[$076F]
```

The write goes to RAM address $076F — but the frame byte for position
19 lives at cs_payload[19] = $0753, which was already filled in phase 1.
The OOB write and the frame byte are at different addresses ($076F vs
$0753).  The frame goes out with the old value.

So:

- **Frame 0:** phase 1 reads $076F (old value) into the frame, then
  phase 2 writes $A5 to $076F in RAM.  Byte [19] = old value.
- **Frame 1:** phase 1 reads $076F again — now $A5, written by frame 0's
  phase 2.  Byte [19] = $A5 if the write succeeded.
- **Frame 2:** same as frame 1 (confirmation).

If byte [19] never changes: the downstream write did not fire (timing
killed it, or the model is wrong).

We stream 3 frames total, then:

```
TX: 30                  STOP
RX: CF                  stop ack (sometimes FE)
```

`consult_reset` runs on stop.  It clears `at_active` ($07B7-$07BC) and
`at_req` ($07AC-$07B1), but NOT `at_values` ($076F-$079C).  A
successful write to $076F survives.

## 8. Independent readback

Re-init, then read the target byte with a clean one-address C9 request.
This is independent of the overrun — no forwarded addresses, no
corruption, just a straight memory read.

```
TX: FF ... FF ... ED
RX: 12                  init ack

TX: C9 07 6F            read $076F
RX: 36 07 6F            echo

TX: F0                  GO
RX: FF 01 xx            frame: 1 byte, xx = current value at $076F
TX: 30                  STOP
RX: CF                  ack
```

### Verdict

| Readback | Baseline | Meaning |
|---|---|---|
| $A5 | not $A5 | **WRITE CONFIRMED.** The downstream primitive works. |
| $A5 | $A5 | Inconclusive — target already had that value. |
| not $A5 | any | **WRITE FAILED.** Timing hazard or model error. |

## 9. Full wire summary

For writing $A5 to $076F from a cold start:

```
--- Init ---
TX: FF (280ms) FF (70ms) ED
RX: 12

--- Baseline ---
TX: C9 07 6F
RX: 36 07 6F
TX: F0
RX: FF 01 xx                   xx = old value
TX: 30
RX: CF

--- Re-init ---
TX: FF (280ms) FF (70ms) ED
RX: 12

--- Write command (60 bytes) ---
TX: C9 5E 00  (x15)            fill
    C9 5E 0A                   repair_a
    C9 5E 0B                   repair_b
    C9 5E 2F                   target ($076F - $0740 = $2F)
    C9 5E A5                   value ($A5)
    C9 07 6F                   probe (direct read, not forwarded)
RX: 36 5E 00  (x15)            echo
    36 5E 0A
    36 5E 0B
    36 5E 2F
    36 5E A5
    36 07 6F

--- GO + stream ---
TX: F0
RX: FF 14 [20 bytes]           frame 0: byte[19] = old value
RX: FF 14 [20 bytes]           frame 1: byte[19] = $A5 if write fired
RX: FF 14 [20 bytes]           frame 2: confirmation

--- Stop ---
TX: 30
RX: CF

--- Re-init + readback ---
TX: FF (280ms) FF (70ms) ED
RX: 12
TX: C9 07 6F
RX: 36 07 6F
TX: F0
RX: FF 01 xx                   xx = $A5 means write confirmed
TX: 30
RX: CF
```

Total: 3 init sequences, ~200 bytes TX, ~200 bytes RX, one write or
zero writes to ECU RAM, key cycle clears everything.
