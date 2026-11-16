# Processor-write research record — 2026-11-15

> **Review added 2026-11-16:** [Write-primitive skepticism and evidence limits](SKEPTICISM.md) distinguishes the observed RAM corruption from unconfirmed chosen-target writes and failed exploit chains. This review involved no new hardware test.

This records existing work on the owned 23710-2L904 engine ECU (Mitsubishi 7700-family main processor and H8 second processor). No implementation, simulation, serial connection, or hardware test was performed for this documentation pass. Starting checkout: `ee89287` (`trying to find write bugs`); the working tree was clean and local main matched the locally recorded origin/main. That does not verify the remote server or recover work absent from this machine.

## Evidence and recovery

- [All 125 existing log files, with sizes and SHA-256](LOGS.md). Raw logs remain in their original locations, unchanged.
- [15 recovered Claude research sessions](SESSIONS.md). Exports preserve message text, tool calls, and available tool outputs, including abandoned ideas, incorrect claims, corrections, and the session-limit ending. Thinking blocks and application metadata are excluded. These are historical evidence, not endorsed operating instructions.
- Existing analysis: [ROM_ANALYSIS.md](../../ROM_ANALYSIS.md), [WRITE_PRIMITIVE.md](../../WRITE_PRIMITIVE.md).
- Existing tools, inspected only: `tools/c9_overrun_test.py`, `tools/c9_actuator_test.py`, `tools/c9_h8_dump.py`, `tools/c9_hidden_read.py`, and `consult/`.

## Current findings

| Finding | Evidence status |
|---|---|
| Oversized forwarded C9 requests corrupt main-processor RAM | Confirmed by recorded before/after values in the overrun log |
| Corruption survives Consult re-init | Supported by successive recorded baselines; full key-cycle reset is an existing research claim, not newly tested |
| A controlled downstream byte write reaches an actuator flag | Earlier claimed; final Claude diagnosis says target addresses never changed. Treat as unconfirmed |
| Stale-value trick plants a hidden-region address into streamlist | Simulation claim; recorded hardware attempt failed |
| Hidden main-processor code was read successfully | No successful read established by available evidence |
| Direct write to H8 program memory, ROM flashing, bank-1 access, or code execution | Not demonstrated |

### Confirmed overrun and its limits

ROM analysis locates `c9_find_hidden` at `$543F`. The forwarded C9 address arrays each hold ten entries, while the command argument buffer can represent twenty addresses. More than ten forwarded addresses overrun those arrays; at iteration 15 (sixteenth address), a 16-bit address store overlaps `c9_hidden_n` (`$07E1`) and the reply cursor (`$07E2`). The index-store destination then depends on the corrupted count.

The direct-store window described by the analysis is `$07C3–$08D6`, 276 bytes inclusive. Address-derived words are restricted to `$0D40–$123F`; index stores contain small loop-counter values. This is a constrained RAM corruption mechanism, not an unrestricted memory writer. The downstream builder at `$9B3F` is modeled as writing `c9_sub_value` through a corrupted payload index into `$0740–$083F` (256 bytes). The union of the two modeled windows is `$0740–$08D6`, 407 bytes inclusive. The old wording calling that union a roughly 275-byte direct-write window was incorrect.

[Overrun log](../../logs/2026-11-15_c9-overrun-test.log) contains four sessions:

| Start time as recorded | Recorded result |
|---|---|
| 17:27:29 | Baseline `$07E2/3/4/5=$00`, `$0817=$00`; after 16 copies of `$5D40` and three frames: `$07E2=$03`, `$07E3=$0C`, `$07E4=$40`, `$07E5=$0D`, `$0817=$0F` |
| 17:30:27 | Baseline retained prior corruption; one frame left cursor `$01` and `$0817=$0F` |
| 17:30:48 | Repeated one-frame result; corruption still present |
| 17:34:09 | Broader 144-byte before/after captures; raw TX/RX retained |

The `$0817=$0F` observation supports the redirected index store. Runtime cursor and flags differ from simplified post-overrun simulations because the reply builder runs afterward. These results do not establish every modeled destination or value combination.

### Actuator-target attempts: success claim withdrawn

[Actuator log](../../logs/2026-11-15_c9-actuator.log) records nine sessions, targeting `$07B7`, `$07BD`, `$07B8`, and `$07B9`. Early trials streamed six frames; later repaired 18/19-address requests streamed 20, 25, 30, or 100 frames. The final saved Claude session re-examined these captures and concluded that no run changed its target address, specifically noting `$07B7` remained `$00` in the 18-address trial.

Earlier descriptions of sustained `$02/$0B` during streaming must not be treated as proof of a write to `at_active`. Payload changes and destination-memory changes are distinct observations. This documentation preserves the final diagnosis as a historical finding; it does not claim a fresh independent decode of all nine captures. Actuator activation and physical relay effects remain unverified through this mechanism.

`at_values` (`$076F–$079C`), `cs_streamlist` (`$07A0–$07A3`), request flags (`$07AC–$07B6`), and active flags (`$07B7+`) are within the modeled downstream range. Parameter overrides, bypassing descriptor validation, indirect H8 signaling, and coordinated multi-byte writes were proposed uses, not established results. Historical session claims also disagree about some test identities and reachable addresses; retain those disagreements as context rather than adopting them as a specification.

### Hidden-code chain: model success, hardware failure

The proposed chain combined downstream writes into `cs_streamlist` with `consult_reply_direct` (`$9CDD`), which reads local bank-0 addresses without the C9 forwarding check. A stale `$07E7` first-frame value was intended to separate the write value from the H8 reply address. Simulations reported 45–65 candidate hidden-region addresses depending on the H8 dump, covering thirteen low-byte values. Those counts describe model outputs only.

A later issue invalidated the simple “plant, re-init, then 0A” sequence: 0A loads streamlist entries from ROM and overwrites the plant. A mixed 0A/C9 sequence was proposed instead. Whether both reply builders interleave as assumed was still an explicit unknown.

[Hidden-read log](../../logs/2026-11-15_hidden-read.log), 20:46:52:

- A 20-address plant targeted `$5E25`.
- Verification sent C9 reads for `$07A0–$07A3`; the reply payload was `00 00 00 00`, so the plant failed.
- After re-init, `0A 02 81` returned `F5 02 FE` instead of `F5 02 81` on all three attempts.
- No successful mixed-command hidden read was established. The rejection occurred after the plant attempt, so it does not by itself identify whether command validity, persistent corruption, or another cause was responsible.

Claude then questioned the stale-write model, revisited the actuator captures, and noted that `c9_find_hidden` runs during F0 processing rather than command echo. Investigation ended with a session-limit/compaction failure. Root cause remains unresolved; “chain works” in the older document is superseded as a hardware claim.

### H8 captures and data quality

The C9 `$5D40–$623F` window forwards to the H8's `$0D40–$123F`, not to its program ROM and not to the main processor's own code at those addresses. This work does not demonstrate writing directly into the H8.

[H8 dump log](../../logs/2026-11-15_h8-dump.log) and [patch log](../../logs/2026-11-15_h8-patch.log) preserve captures. Existing artifacts include `h8dump.bin`, `h8_clean.bin`, `h8_mv.bin/.txt`, `h8_mv2.bin/.txt`, and `h8_consensus.bin/.txt` in the repository root.

Recovered research found batch-8 captures had constant `0E 1E` in positions 6–7 of all 160 blocks: 320 of 1280 bytes were artifacts. The patch replaced exactly those positions, but recurring `$98` on a 24-byte stride raised another contamination concern. The name `h8_clean.bin` therefore does not establish trustworthy data. Later majority-vote and consensus work is preserved in the sessions and artifacts; consensus of repeated captures is not independent validation of the decoder. Simulated target counts derived from these files inherit their data-quality limits.

A prior session also added a ten-address limit to ordinary `sub-dump` requests. That existing implementation was not altered here. The underlying overflow concerns the hidden-address arrays, despite some historical messages mistakenly naming `cs_argbuf` as the overflowing array.

### Other reviewed paths and conclusions

The earlier audit found a separate mixed 5A/C9 argument off-by-one reaching `$08FA`, described as dead padding; a direct-mode `$80` value underflow selecting unintended fixed ROM descriptors; fixed normal 0A value destinations; and fixed bank-0 reads. Config bytes `$1206/$1207` were described as immutable ROM without a writable shadow. `$1207=$52` has bit `$20` clear, so `$FE00–$FFCF` is already locally C9-readable on this ECU.

Claims that no RAM function-pointer transfer exists apply to the inspected image and analysis coverage; the hidden main-CPU region and bank 1 are not fully available. Do not elevate this to a proof that code execution is universally impossible. Likewise, earlier absolute conclusions that streamlist cannot be influenced were superseded by discovery of the overrun, but a useful streamlist plant still has not been demonstrated.

## Remaining unknowns, recorded without further development

1. Why the reply-builder/stale-value simulation disagrees with the actuator and plant captures.
2. Whether any controlled downstream target-memory write can be shown independently of reply payload changes.
3. Why direct-mode value `$81` was rejected after the failed plant.
4. Whether a mixed 0A/C9 stream executes both builders as assumed.
5. Which H8 bytes are stable data rather than frame artifacts, and how that affects simulated candidate addresses.
6. Whether any proposed parameter/flag manipulation produces the intended physical effect.

No new tests, tool changes, commits, or pushes were performed in this documentation pass. The preserved record includes failed and superseded work so a future reader can resume from the actual stopping point.
