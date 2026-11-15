# Body units: service-manual reference and remaining work

What the 1998 Maxima service manual (`fsm/EL.pdf`, pages EL-nnn) says about the IVMS
and ASCD, and what's left to map. Byte-level results are in [`BCM.md`](BCM.md).

## IVMS layout (EL-164 … EL-197)

| Unit | Role |
|---|---|
| BCM | Master; the only IVMS unit Consult talks to |
| LCU01 | Driver door |
| LCU02 | Passenger door |
| LCU03 | Rear RH door |
| LCU04 | Rear LH door |
| LCU05 | Multi-remote (keyless entry) |

LCUs link to the BCM over two multiplex lines (A-1, A-2). Some IVMS functions stop while
Consult is connected (EL-168), e.g. the intermittent wiper during data monitor (EL-101).

## Consult functions per test item (EL-168)

| Test item | Self-diag | Data monitor | Active test | BCM item group |
|---|:-:|:-:|:-:|---|
| IVMS-COMM CHECK | ✓ | | | |
| POWER WINDOW | | ✓ | ✓ | `1` |
| DOOR LOCK | ✓ | ✓ | ✓ | `2` |
| MULTI-REMOTE CONT SYS | | ✓ | ✓ | |
| THEFT WARNING SYSTEM | | ✓ | ✓ | `C` |
| ROOM LAMP TIMER | | ✓ | ✓ | `9` |
| STEP LAMP | | ✓ | ✓ | `E` |
| ILLUM LAMP | | ✓ | ✓ | `F` *(inferred)* |
| IGN KEY WARN ALM | | ✓ | ✓ | `7` / `8` / `B` |
| LIGHT WARN ALM | | ✓ | ✓ | `7` / `8` / `B` |
| SEAT BELT TIMER | | ✓ | ✓ | `7` / `8` / `B` |
| WIPER | | ✓ | ✓ | `5` |
| REAR DEFOGGER | | ✓ | ✓ | `6` |

## Item names

**Data monitor (switches):** IGN ON SW, IGN ACC SW, IGN KEY SW, HD/LMP 1ST SW, SEAT
BELT SW, DOOR SW-DR, DOOR SW-AS, DOOR SW, HOOD SWITCH, TRUNK SWITCH, TRUNK UNLK SW,
TAMPER SW-TRK, TRUNK BTN-CON, INT SW, WASH SW, DEFOGGER SW, VHCL SPEED SE, LOCK SIG-DR,
DOOR LK SW-LK, DOOR LK SW-UN, KEY CYL LK-DR, KEY CYL LK-AS, KEY CYL UN-AS, P/W SW
DR-AUT / DR-DWN / AS-UP / AS-DWN / RL-UP / RL-DWN, MAIN SW AS-UP / RL-UP / RR-DWN.

**Analog:** INT RESIST (wiper knob, 0 to ~1 kΩ).

**Active tests:** WIPER AMP, LIGHT WARN ALM, IGN KEY WARN ALM, SEAT BELT WARN ALM,
HAZARD, RR DEFOGGER RLY, DR LOCK MTR (per door), ALARM RELAY, INTERRUPT RELAY (starter
cut), INDICATOR LAMP (security), room / step / illumination lamps, power windows.

## IVMS communication diagnosis (EL-172 … 177)

| Unit | COMM FAIL | NO RESPONSE |
|---|---|---|
| LCU01 driver door | 24 | 25 |
| LCU02 passenger door | 34 | 35 |
| LCU03 rear RH | 41 | 42 |
| LCU04 rear LH | 44 | 45 |
| LCU05 multi-remote | 54 | 55 |
| No malfunction | 11 | |

Consult results per unit: NO FAILURE, [COMM FAIL], [NO RESPONSE], [SLEEP], [PAST COMM
FAIL], [PAST NO RESPONSE]. Erase: Consult, or pull the 7.5 A fuse.

**Door lock self-diag (EL-221):** DOOR LOCK MOTOR-DR, -AS, -RR/RH, -RR/LH (actuator or
unlock-sensor circuit).

## On-board modes (no tool, EL-175 …)

| Mode | Function | Page |
|---|---|---|
| I | Communication diagnosis (blink codes above) | EL-176 |
| II | Switch monitor: lamp blink + chime for each switch the BCM sees | EL-178 |
| III | Door-lock self-diag | EL-222 |
| IV | Power-window monitor | EL-205 |

## ASCD cruise unit (EL-150, 151)

Needs the ASCD MAIN switch ON. Its Consult ID hasn't been found.

| Function | Items |
|---|---|
| Self-diag | POWER SUPPLY-VALVE, VACUUM PUMP, AIR VALVE, RELEASE VALVE, VHCL SP-S/FAILSAFE, CONTROL UNIT, BRAKE SW/STOP/L SW |
| Data monitor | BRAKE SW, STOP LAMP SW, SET SW, RESUME/ACC SW, CANCEL SW, VHCL SPEED SE, SET VHCL SPD (mph), VACUUM PUMP, AIR VALVE (ms), PW SUP-VALVE, CRUISE LAMP, A/T-OD CANCEL, FAIL SAFE-LOW, FAIL SAFE-SPD |
| Active test | None |

## Status

| Area | Status |
|---|---|
| Find units | ✅ `DA` BCM, `DC` airbag, `E7` ABS. ASCD not found |
| BCM identify | ✅ `D0`. `D1` unsupported; `C1` untested |
| BCM data monitor | ◐ Switch block mostly mapped |
| BCM active tests | ◐ Starter interrupt, security indicator, illumination not found |
| BCM ROM | — Not readable over Consult |
| IVMS COMM / WAKE-UP diagnosis | ☐ Needs a capture from a real CONSULT |
| ASCD | ☐ |

## Remaining work

1. Find the ASCD unit: init scan with the MAIN switch ON, KOER.
2. Map the rest of the switch block; cross-check every switch with Mode II.
3. Find the starter interrupt, security indicator and illumination tests.
4. Capture a genuine CONSULT (passive tap on TX/RX at 9600 8N1) for the IVMS COMM /
   WAKE-UP diagnosis and erase commands.
