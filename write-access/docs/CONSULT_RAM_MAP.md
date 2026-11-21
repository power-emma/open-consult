# Consult downstream RAM write window: $0740–$083F

Offline review of ECU 23710-2L904 (1998 Maxima VQ30DE M/T), 2026-11-16.
This maps the **256-byte downstream reply-builder window**, not every address
the initial array overflow might corrupt. No commands were sent to hardware.

## What this access would add

The main opportunities are temporary diagnostic overrides, access to an
otherwise rejected override handler, manipulation of diagnostic bookkeeping,
and potentially redirected diagnostic reads. This window contains neither the
ROM calibration maps nor the ordinary live fuel-trim, timing and sensor values.
It is not evidence of reflashing, persistent tuning or code execution.

The write mechanism and controllable data are separate questions. The notes in
the [write-access guide](../README.md) and [`consult/write.py`](../../consult/write.py) report repeatable $93 writes with
the engine off. Earlier experimental scripts still describe controlled writes
as unconfirmed. `logs/2026-11-16_c9-tapsweep.log` includes a post-reinit C9 read
of $0817 returning $93; that supports that observed readback, not arbitrary-byte
control, every destination, or a guarantee of no collateral writes. Treat the
capabilities below as conditional on a verified write to the particular target.

## Complete region map

All ranges are inclusive. Gaps remain explicitly unidentified. The linked CSV
contains one row for each of the 256 bytes, with literal instruction references.

| Address | Role and ROM evidence | Meaning of a write / normal replacement |
|---|---|---|
| $0740–$0767 | Consult reply payload; $99BD, $9A54, $9AC7, $9AEE, $9B59, $9CE4 | Alters diagnostic output bytes. Reply builders replace them; changing a reported value does not establish a change in engine control. |
| $0768–$0769 | Unidentified gap after payload; $9A90 compares against end pointer $0768 | No independent control function established. End-pointer references are not reads of this RAM. |
| $076A | Direct-mode selection mask; $5169–$5182, $51CA–$51DE, $5263–$5277 | Changes parser branch selection when consumed. A new direct-mode selection replaces it. |
| $076B | Direct-mode value; $51C6, $5239, $5260, $9CE7 | Influences direct-mode setup/reply format; replaced by a new direct-mode value. |
| $076C–$076D | Direct-mode stream length and iteration counter; $51EA–$5224, $9BF7, $9CDD–$9D3A | Can disrupt read iteration and response length. Counter is reset by the builder; length by mode setup. |
| $076E | DTC reply scan pass; $99DF, $9A0C, $9A22, $9A5C, $9AA6 | Changes DTC reply construction, not stored fault flags. Builder initializes it. |
| $076F–$079C | Active-test value slots; store $519D, descriptor table $1160–$11BB | Temporary override parameters when the matching flag/handler is active. Normal test commands replace individual slots. Not all slots have supported descriptors or visible handlers. |
| $079D–$079F | Unidentified gap | No independent function established. |
| $07A0–$07AB | Direct-mode stream address list, up to six 16-bit entries; $5224, $5327, $5331, $9CF1, $9D10 | A controlled pointer could redirect diagnostic reads within bank 0. Mode setup normally reloads the list from ROM. See limitations below. |
| $07AC–$07B1 | Requested active-test flags; $514E–$5152, $536F–$537E | Requested flags are committed to active flags on the relevant F0 path. Stop/reinit clears these six bytes at $54F8–$54FE. |
| $07B2–$07B6 | Second-CPU received data; $CA13, $CA19, $CA27–$CA33, $CA65 | Incoming mailbox messages replace these bytes. Physical interpretation remains incomplete. They are not additional requested-test flag bytes. |
| $07B7–$07BC | Active-test flags in force; $5372–$537E; consumers below | Can gate mapped override handlers. Stop/reinit clears these six bytes at $5501–$5507; a later test commit replaces them. |
| $07BD–$07C1 | Second-CPU received data; $CA39–$CA51 | Incoming mailbox messages replace these bytes; physical meanings unresolved. |
| $07C2 | UART status snapshot; $4F08, $4F15, $4F67, $4F77, $4FA9, $4FC8, $534B, $53F3 | Can disturb receive/echo handling. ISR entry refreshes it. |
| $07C3–$07D6 | Ten forwarded-address words; $549A/$54A0, $9B75–$9B7B | Changes the addresses requested from the second processor. Forwarded request setup rebuilds entries. |
| $07D7–$07E0 | Ten forwarded-reply placement indices; $54AA/$54B2, $9B4F | Changes where forwarded bytes land in the reply buffer or surrounding RAM. This is the downstream write mechanism itself. |
| $07E1–$07E3 | Forwarded count, cursor, flags; $5442, $544D, $54B4, $9B2A–$9B6C | Changes reply processing and write scheduling. Count/flags initialized by forwarded setup; cursor advanced by builder. Overflow also clobbers them. |
| $07E4–$07E7 | Forwarded address word, request flag, returned byte; $9B7B–$9B85, $CD59–$CD67, $C862 | Controls forwarding state/data. Returned byte $07E7 is replaced by mailbox reception, explaining loss of chosen-value control. |
| $07E8–$07EB | Received second-CPU status; $C819–$C851; consumers include $7242, $79D7, $831B, $9572 | Temporary status corruption may affect dependent control/diagnostic branches. Incoming messages refresh these bytes. Bit meanings incomplete. |
| $07EC–$07ED | Unidentified gap | No independent function established. |
| $07EE–$07F4 | Composite control/diagnostic flags; $D926–$DB7A; sent via $CD8F–$CDC5 | Can affect diagnostic/control branches and outbound second-CPU status. Recomputed or modified by normal tasks; not a proven direct actuator interface. |
| $07F5 | Unidentified gap | No independent function established. |
| $07F6 | Handshake/diagnostic state bits; e.g. $C874, $CC5B–$CC92, $D3C4, $D19C–$D1B0 | Can alter sequencing; individual bits updated by mailbox and diagnostic tasks. |
| $07F7 | Working value sent to second CPU; writers $409E, $584C, $588E; reader $CCD1 | Transient change to outbound data; physical meaning not established here. |
| $07F8–$07FA | Received second-CPU data; $C811, $C856, $C867; $CAD7 reads $07F9 | Replaced by reception; $07F9 also cleared at $CB99. |
| $07FB–$07FC | Command-dispatch results; $CAF4–$CB9D; outbound $CDCF/$CDD4 | Changes data sent to second CPU. Dispatch normally replaces them; command semantics incomplete. |
| $07FD–$0800 | Two working words based at $07FD/$07FF; $BBC9–$BC68 | Used in comparison/clamping logic in the idle-air calculation area. Normal calculations replace them; units and full effect unresolved. |
| $0801–$0804 | Working control state; $8BA4/$8BA9 ($0801), $7A2B/$81DA–$81F8/$8B7D ($0802), $6EE3/$6EE9 ($0803); $0804 unresolved | Temporary control-state changes possible; insufficient mapping for a specific useful function. |
| $0805–$0807 | Purge-step working/output state; $444A, $94B3, $BF6F–$C0B7 | $0806 is the mapped purge step; $0805 companion state; $0807 sequencing bits. Purge task updates them. A changed RAM step is not proof of commanded valve movement. |
| $0808–$0809 | Purge-related flags/counter; $40D0, $40F1, $4137, $BDD1–$BECD; $3DD4, $936A/$936F, $BCB3 | Changes state used by purge calculations; updated by normal tasks. Exact bit meanings unresolved. |
| $080A–$080F | Working sample history/calculated value; $8A34, $8A53–$8A89, $E89C–$E8A8 | Can disturb subsequent calculations; refreshed by sample shifting/initialization. Sensor identity not established here. |
| $0810–$0822 | Nineteen bytes of faults seen this ignition cycle; $503D–$507F, $9C04–$9C45, $D38C, $DEA1 | Changes cycle bookkeeping and hidden 51 reporting, not the stored confirmed/pending DTC arrays. Detection paths set bits again; 51 clears this region. |
| $0823–$0828 | Unidentified gap | No independent function established. |
| $0829–$082B | Second-CPU received values; $C951–$C95D | Incoming messages replace them; physical meanings unresolved. |
| $082C | Control/status bits; $7389, $78BA, $8379, $8CFD, $919B, $92FB, $DDF1, $DE67; outbound $CD0E | Influences several branches and is sent to second CPU; no complete bit mapping. |
| $082D | Unidentified gap | No independent function established. |
| $082E | Received second-CPU value; $C87A | Replaced on reception; meaning unresolved. |
| $082F | Unidentified gap | No independent function established. |
| $0830–$083F | First 16 bytes of nineteen-byte first-trip-handled array $0830–$0842; $DEC1–$DEE5, $DF97 | Can alter whether detection is handled again during this cycle. Stored pending faults are at $0580, outside this window. Last three array bytes are also outside the window. |

## Active-test consumers: useful distinctions

The existing [active-test table](../../ROM_ANALYSIS.md#4-active-tests-0a-descriptor-table-at-1160-rom)
maps supported flags/values. Directly checked bank-0 consumers include:

| State | Consumer | What the code establishes |
|---|---|---|
| Fuel override | $6E15–$6E31; additional gate $7434 | Reads $0770 when $07B7 bit $02 is active; clamps to $4B–$7D (75–125%). Writing RAM does not remove this clamp. |
| Idle-air override | $ACB3–$ACC1 | Reads $0774 when $07B7 bit $20 is active; clamps to $81. Earlier branch $ACA0 can select another path. |
| Additional idle-air path | $ACA0–$ACAC | $07B8 bit $10 selects a fixed-calibration path via $BC22/$22AF. |
| Rejected test 83 handler | $B39A–$B3A8 | $07B7 bit $08 selects $0772, clamps it to $90, writes $0BCD. Descriptor for 83 is unsupported. Physical meaning remains unresolved; this is a candidate capability beyond the normal parser. |
| Purge override | $BFB3–$BFC5 | $07BA bit $01 selects $0787 within the purge calculation. |
| A2 output override | $F4C0 onward | $07BB bit $04 selects a zero/nonzero value from $0791 for an output-control path. Physical actuator identity is only weakly inferred in existing notes. |
| AB diagnostic sequence | $98BB/$992E | $07BC bit $08 selects logic that uses $079A and backup RAM. A temporary flag can cause effects outside this write window. |
| AA stop side effect | $5406 | $07BC bit $04 at stop sets backup-RAM $0F69 bit $10. Do not assume a key cycle undoes every downstream effect. |

Coolant, timing, cylinder cut and relay tests also have descriptors, but some
handlers are in unread bank 1 or involve the second processor. Writing their
flag is not by itself proof the expected actuator command executes. The
`write-access/tools/c9_actuator_test.py` header specifically records that relay control was
not explained by the visible bank-0 flag consumers.

Writing $93 to $07B7 would set multiple bits together; it is not a clean
single-test selection. Likewise $93 in the fuel-value slot would be clamped,
if consumed by the mapped override path. These are consequences of the code,
not recommendations to run those writes.

## Redirected reads: plausible, already attempted, not demonstrated

The direct reply builder reads a 16-bit address from $07A0,X then dereferences
it at $9CF7/$9D15, without C9's forwarding-range substitution. With controlled
pointer bytes and suitable sequencing, this could expose the main CPU's local
$5D40–$623F region instead of forwarding those reads to the second processor.
It would still be a bank-0 read, not bank 1 access.

There are two obstacles: direct-mode setup normally replaces the pointer list,
and chosen two-byte writes have not been established by the $93 primitive.
`write-access/tools/c9_hidden_read.py` already proposes a mixed-command chain and explicitly
marks it failed in the recorded hardware trial. The corresponding
`logs/2026-11-15_hidden-read.log` records repeated FE rejection of the requested
direct-mode setup. The older ROM notes' claim that no Consult write can ever
reach $07A0 is therefore too broad under the assumed downstream write, but a
successful hidden read still cannot be claimed.

## Scope and reproducibility

- Source: [annotated ROM listing](../../rom/23710-2L904.asm), its `.ann` file,
  [ROM analysis](../../ROM_ANALYSIS.md), and the scripts/logs named above.
- [Per-byte literal reference index](CONSULT_RAM_XREFS.csv): regenerate with
  `python3 write-access/tools/consult_ram_xrefs.py > write-access/docs/CONSULT_RAM_XREFS.csv`.
- The index records instruction operands, including immediate constants and
  indexed bases, not a complete read/write graph. Computed-pointer accesses,
  word-access second bytes, initialization loops, unread bank 1 and the second
  processor require manual analysis. Zero references does not mean unused RAM.
- Several existing documents contain conclusions from different research
  stages. This map preserves the distinction between visible instructions,
  recorded readbacks, and inferred physical effects.
- Original Nissan bulletin was located; factory authorization is established by this analysis.
