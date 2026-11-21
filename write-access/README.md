# Write access to Nissan ECU RAM over Consult

This folder keeps the write-access research together:

- [`nissan-write.py`](nissan-write.py): offline payload builder and simulator.
- [`docs/`](docs/): RAM map, direct-write test notes, and the literal-reference index.
- [`tools/`](tools/): C9 and H8 research tools. Run their documented commands from
  the repository root. Live tools can change ECU state; review each tool before
  connecting it to a vehicle.
- [`h8/`](h8/): H8 dumps and comparisons previously kept at the repository root.

Session logs remain in the repository's [`logs/`](../logs/) directory. The
runtime library stays at [`consult/write.py`](../consult/write.py), where the
research tools import it.

Nissan's own Consult-I tool can write a byte to any address in
`$0740`-`$083F` (256 bytes of live ECU working RAM) using the `C9`
memory-read command with a specific 20-address payload. A Nissan service
bulletin documents this as an authorized diagnostic procedure.

I reverse-engineered this independently before finding the bulletin —
the mechanism below is what the factory tool does under the hood.

**Confirmed on hardware:** 25/25 writes on a 1998 Maxima (ECU 23710-2L904).
The written byte persists across diagnostic stop and reinit. A key cycle
clears it.

## How it works

The ECU's `c9_find_hidden` routine (`$543F`) processes queued `C9` addresses
that fall in the second-processor forwarding window (`$5D40`-`$623F`). It
appends each to a 10-entry array pair (`c9_hidden_addr` at `$07C3`,
`c9_hidden_idx` at `$07D7`). The loop terminator compares against `cs_argc`
(how many addresses you sent), not the array capacity, so a single `C9`
request can queue 20 addresses all inside the forwarding window. From entry
10 onward, the stores walk off the arrays into live handler state.

At entry 15 the 16-bit address store lands on `c9_hidden_n` / the reply
cursor (`$07E1`/`$07E2`), writing caller-controlled data. This redirects
the downstream reply builder's index, so its per-frame store at `$9B5E`
(`cs_payload[idx] = c9_sub_value`) writes through the redirected offset
into the surrounding 256-byte region.

## The 20-address payload

```
Position   Address    Effect
--------   -------    ------
[0..14]    fill x15   Fill arrays normally, overrun starts at i=10
[15]       $5E0A      Sets n=$0A, cursor=$0E
[16]       $5E0B      Repairs flag byte $07E3 (bits 0+1 set)
[17]       $5E00+T    Plants target offset T into idx[$0E]
[18]       $5E00+V    Writes V into c9_sub_value (clobbered by H8 FIFO)
[19]       $5E00      Dummy
```

Where `T = target_addr - $0740` and `V = desired value byte`.

Position 18's value is overwritten by the H8 FIFO response before the
builder reads it. The actual written byte comes from the FIFO drain
position, not from V. Double-tap (two back-to-back overruns of 1 frame
each) deterministically writes `$93`.

## Code

[`nissan-write.py`](nissan-write.py) is a self-contained script that
computes the payload and simulates the overrun. No serial connection needed.

```
python3 write-access/nissan-write.py --target 0817
python3 write-access/nissan-write.py --target 07B7 --sim
```

## Constraints

| Constraint | Detail |
|---|---|
| Destination | `$0740`-`$083F` (256 bytes) |
| Value | `$93` at key-on / engine-off (deterministic). `$99`-`$9B` with engine running (live sensor data, not controllable). Arbitrary value control not achieved |
| Persistence | Survives diagnostic stop/reinit. Key cycle clears |
| Code execution | Impossible -- no RAM function pointer exists in the ROM image |

## Nissan service bulletin

A Nissan service bulletin describes this exact write mechanism as an
authorized diagnostic procedure — the factory Consult hand-held uses it
to write ECU RAM during certain service operations. I found this after
independently discovering and documenting the mechanism from the ROM
disassembly.

## Research notes

Additional analysis is in [the write-access docs](docs/); evidence logs are
in the repository's [`logs/`](../logs/) directory.
