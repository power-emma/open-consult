# Write-primitive evidence review — 2026-11-16

**Assessment: the saved evidence supports a reachable buffer overflow with observed main-processor RAM corruption. It does not establish an unrestricted memory writer, reliable actuator control, hidden-code extraction, ROM writing, or code execution.**

This review inspected the saved disassembly and the first overrun session's raw TX/RX. It performed no new hardware test or independent instruction-level emulation. The actuator conclusions below rely on the corrected research record and its preserved final diagnosis, rather than a fresh decode of every actuator capture.

## What supports a real finding

In [the saved disassembly](../../rom/23710-2L904.asm), `c9_find_hidden` at `$543F` appends forwarded addresses and request indices to ten-entry arrays. Its termination check at `$54C0–$54C4` uses the request argument count; there is no ten-entry capacity check before the stores at `$54A0` and `$54B2`.

The strongest recorded observation is in [the overrun log](../../logs/2026-11-15_c9-overrun-test.log), first session at 17:27:29:

- Before the oversized request, the raw five-byte readback is `00 00 00 00 00` for `$07E2`, `$07E3`, `$07E4`, `$07E5`, and `$0817`.
- Afterward, the raw readback is `03 0C 40 0D 0F` for those same addresses.
- In particular, `$0817` changes from `$00` to `$0F`. The predicted mechanism is that the sixteenth address store overwrites the count with low byte `$40`, then the index store writes request index 15 to `$07D7 + $40 = $0817`.

This agreement between a specific predicted destination/value and raw readback is stronger evidence than the script printing “BUG CONFIRMED.” It supports a real constrained write beyond the arrays. The other changed bytes include live reply state and should not all be attributed solely to the initial overflow stores: the reply builder also runs before readback.

## What the primitive actually controls

The direct stores contain address-derived words restricted to `$0D40–$123F`, or request indices in the range 0–19. Corrupting the count influences subsequent destinations, but destination, value, iteration, and surviving handler state are coupled. Calling this an “arbitrary write” without those qualifications overstates the result.

The analyzed direct-store envelope is `$07C3–$08D6`. It is a possible address envelope, not proof that every byte/value pair within it is independently selectable or has been demonstrated on hardware. Actuator flags and streamlist entries below `$07C3` require the proposed downstream mechanism; the direct overrun cannot itself establish those claims.

The downstream store at `$9B5E` uses a corrupted index to place `c9_sub_value` relative to `$0740`. The code supports concern about another out-of-bounds write, with an analyzed envelope of `$0740–$083F`. A useful chosen-target write still depends on reaching that store with the intended cursor, flags, handshake, index, and value. The failed experiments show that the existing simulation does not establish those runtime conditions.

## Why the stronger success claims are unreliable

| Claim | Reason for skepticism |
|---|---|
| Actuator flags were successfully written | The preserved final review withdrew this claim and reported unchanged target addresses. Bytes appearing in a streamed payload are not proof that the target RAM byte changed. |
| The stale-value trick plants a chosen streamlist address | The recorded hardware attempt read back `00 00 00 00` from the intended streamlist entries. Simulation success did not transfer to that attempt. |
| Re-init followed by 0A reads the planted hidden address | The later analysis found that 0A reloads streamlist entries from ROM, overwriting the proposed plant. The replacement mixed-command chain was not demonstrated. |
| Dozens of hidden-code bytes are accessible | The counts came from simulations using H8 captures with documented framing/artifact concerns. No successful hidden-code read was established. |
| Corruption permits code execution or ROM writes | Neither was demonstrated. Conversely, incomplete coverage of hidden code and bank 1 also prevents treating “code execution is impossible” as a universal proof. |

See [the corrected findings](FINDINGS.md) for the failed plant, withdrawn actuator claim, capture-quality concerns, and links to the preserved sessions. Repeated claims across session text, Python models, and documentation are not independent confirmations when they share the same assumptions.

## Evidence needed to strengthen the claim

A reliable chosen-target writer would need independent target-memory readback showing the intended change, with destination and value varied across examples and unintended changes accounted for. Payload contents alone are insufficient. The model/hardware disagreement must be explained before its simulated reachability counts or stale-value chain are treated as established behavior.

A hidden-read claim additionally needs evidence that the planted pointer survives the command sequence and that the returned byte comes from the intended main-processor address rather than the H8, a fixed descriptor, or a framing artifact. An actuator-effect claim needs evidence beyond flag placement to establish the claimed physical effect.

Until then, retain **“reachable buffer overflow with recorded RAM corruption”** as the finding. Label the downstream writer and proposed chains as unconfirmed. The older categorical success statements are unsupported overclaims; that does not make the underlying overflow imaginary.
