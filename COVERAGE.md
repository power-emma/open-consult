# Consult coverage: what the FSM says exists vs. what we've mapped

Every Consult function the 1998 Maxima FSM lists for this car, matched to the bytes we
know. Sources: GI-34 (which unit has which mode), EC-64 … EC-74 (engine), EL-150/151
(ASCD), EL-168 and the IVMS system sections (BCM), RS-25 … RS-27 (airbag), BR-39 / BR-44
(ABS). A/T is left out (manual car, no unit at `EA`).

**Grades**

| Mark | Meaning | Score |
|---|---|---|
| ✅ | Command bytes known **and** confirmed on the car | 1 |
| ◐ | Bytes identified (ROM, PLMS, or a read/test we've seen respond), but meaning inferred or only partly decoded | ½ |
| ☐ | No byte known | 0 |

VOLTAGE and PULSE (EC-70) are CONSULT's own probe inputs, not ECU data, so they are not
counted. Work support and function tests are tool-side procedures built from data
monitor items and active tests; they're graded on whether we have the parts.

## Summary

| Unit | Init | Items | ✅ | ◐ | ☐ | Strict (✅ only) | Weighted |
|---|---|---|---|---|---|---|---|
| Engine ECM | `ED` | 108 | 33 | 41 | 34 | 31 % | **50 %** |
| BCM (IVMS) | `DA` | 35 | 12 | 17 | 6 | 34 % | **59 %** |
| Airbag | `DC` | 5 | 1 | 3 | 1 | 20 % | **50 %** |
| ABS | `E7` | 24 | 1 | 0 | 23 | 4 % | **4 %** |
| ASCD | ? | 22 | 0 | 0 | 22 | 0 % | **0 %** |
| **All units** | | **194** | **47** | **61** | **86** | **24 %** | **40 %** |

Excluding DTC work support (19 engine tests that only matter for OBD drive-cycle
confirmation): engine 60 %, all units 44 %.

The low-level view is better than the FSM view, because whole command sets were scanned:

| Unit | Command bytes | Read space | Test space |
|---|---|---|---|
| Engine | Complete from ROM: `FF 30 5A C9 0A D0 D1 C1 51` | 73 registers supported; ~64 named (open: `20 28 2A 32 3A 4C 4F 60`, `61` partly) | 22 descriptors `80–AD`; 15 named, 7 open (`8C 95 99 A6 AA AC AD`) |
| BCM | Complete from a full byte probe: `FF 30 5A 9E C9 D0 0A`; `C1` untested | 21 items found (12 `x2` = one per IVMS system, plus `FF 15 19 1A 1B 25 2B 35 3B`); switch block mostly mapped, other items mostly undecoded | Every `x3` group scanned; 7 more echoed items `05 09 0A 11 1B 3B FE` with no known function |
| Airbag | Probe: `5A C9 D0 D1` echo | Registers `8A 8B 9A AB AC`; `C9` rejects every address | Not applicable (none, and don't) |
| ABS | Probe: only `D0` answers; `9E 9F D1` go silent (waiting for more bytes?) | None | Not probed (never send `0A`) |

## Engine ECM (`ED`)

### Data monitor (EC-67 … EC-70): 49 items, 17 ✅ 22 ◐ 10 ☐

| FSM item | Reg | | Note |
|---|---|---|---|
| CKPS·RPM (POS) | `00/01` | ✅ | |
| CKPS·RPM (REF) | `02/03` | ✅ | Period, rpm = 2 500 000 / word |
| POS COUNT | | ☐ | |
| MAS AIR/FL SE | `04/05` | ✅ | |
| COOLAN TEMP/S | `08` | ✅ | |
| FR O2 SEN-B1 / -B2 | `09` / `0A` | ◐ ◐ | Values ✅; which bank is which: open |
| RR O2 SENSOR | `35` | ◐ | PLMS |
| FR O2 MNTR-B1 / -B2 | `21` b7 / b6 | ◐ ◐ | Bits ✅; bank open (follows `09`/`0A`) |
| RR O2 MNTR | | ☐ | |
| VHCL SPEED SE | `0B` | ✅ | |
| BATTERY VOLT | `0C` | ✅ | |
| THRTL POS SEN | `0D` | ✅ | |
| TANK F/TMP SE | `2A` | ◐ | PLMS guess |
| EGR TEMP SEN | `10` | ◐ | PLMS |
| INT/A TEMP SE | `11` | ◐ | Scaling unchecked on the car |
| START SIGNAL | `13` b1 | ◐ | Generic bit, untested |
| CLSD THL/P SW | `13` b0 | ✅ | |
| AIR COND SIG | `13` b4 | ✅ | |
| P/N POSI SW | `13` b2 | ✅ | |
| PW/ST SIGNAL | `13` b3 | ✅ | |
| LOAD SIGNAL | `13` b5 | ✅ | |
| IGNITION SW | | ☐ | |
| INJ PULSE-B1 / -B2 | `14/15`, `22/23` | ✅ ✅ | |
| B/FUEL SCHDL | | ☐ | Candidate `28` (no bank-0 writer) |
| IGN TIMING | `16` | ✅ | |
| IACV-AAC/V | `18` | ◐ | ROM |
| PURG VOL C/V | `29` | ◐ | ROM, strong |
| ENGINE MOUNT | | ☐ | Weak lead: `49` b2 (test `A2`) |
| A/F ALPHA-B1 / -B2 | `1A` / `1B` | ✅ ✅ | |
| EVAP SYS PRES | | ☐ | Lead: `3A` |
| AIR COND RLY | `1E` b1/b7 | ◐ | Relay vs fan bit open |
| FUEL PUMP RLY | `1E` b6 | ◐ | |
| COOLING FAN | `1E` | ◐ | Bits not seen yet (≤ 92 °C) |
| EGRC SOL/V | `1F` b0 | ◐ | Weak |
| VENT CONT/V | | ☐ | |
| FR O2 SEN HTR-B1 / -B2 | `30` b6/b5 | ◐ ◐ | ROM |
| RR O2 SEN HEATER | | ☐ | |
| VC/V BYPASS/V | | ☐ | |
| PURG CONT S/V | | ☐ | |
| CAL/LD VALUE | `33/34` | ◐ | PLMS |
| ABSOL TH·P/S | `37` | ◐ | PLMS |
| MASS AIRFLOW | `38/39` | ◐ | ROM + PLMS |
| MAP/BARO SW/V | `49` b3/b5 | ◐ | ROM |
| ABSOL PRES/SE | `4A` | ◐ | PLMS |

### Active tests (EC-71/72): 15 items, 2 ✅ 9 ◐ 4 ☐

| FSM item | Test | | Note |
|---|---|---|---|
| FUEL INJECTION | `81` | ◐ | ROM: clamp `4B–7D` |
| IACV-AAC/V OPENING | `85` | ◐ | ROM |
| ENG COOLANT TEMP | `80` | ◐ | |
| IGNITION TIMING | `82` | ◐ | |
| POWER BALANCE | `88` | ✅ | `01` cuts cylinder 1 |
| COOLING FAN | `93`/`94` | ✅ | |
| FUEL PUMP RELAY | `89` | ◐ | |
| EGRC SOLENOID VALVE | | ☐ | One of `95 99 A6 AC AD`? |
| SELF-LEARNING CONT | `8B` | ◐ | |
| ENGINE MOUNTING | | ☐ | Weak lead: `A2` |
| PURG VOL CONT/V | `98` | ◐ | ROM, strong |
| VENT CONTROL/V | `9A` / `AB` | ◐ | PLMS |
| VC/V BYPASS/V | `9C` / `A7` | ◐ | PLMS |
| PURG CONT S/V | | ☐ | |
| MAP/BARO SW/V | | ☐ | |

### Self-diagnosis, part number (EC-64/65): 6 items, 4 ✅ 2 ◐

| Item | Bytes | |
|---|---|---|
| DTCs | `D1` | ✅ |
| 1st-trip DTCs | `D1` (starts = `F5`) | ✅ |
| Erase | `C1` | ✅ |
| Freeze frame | `3B–47`, `51` | ◐ (order unconfirmed) |
| 1st-trip freeze frame | `56–5F` | ◐ |
| ECM part number | `D0` | ✅ |

### Work support (EC-65): 4 items, 1 ✅ 3 ◐

| Item | Built from | |
|---|---|---|
| THRTL POS SEN ADJ | `0D` | ✅ |
| IACV-AAC VALVE ADJ | Probably a fixed-idle test (`8C`?) | ◐ |
| FUEL PRESSURE RELEASE | `89` | ◐ |
| EVAP SYSTEM CLOSE | Vent + VC bypass tests | ◐ |

### Function tests (EC-73/74): 14 items, 9 ✅ 4 ◐ 1 ☐

✅ SELF-DIAG RESULTS, CLOSED THROTTLE POSI, THROTTLE POSI SEN CKT, PARK/NEUT POSI SW
CKT, COOLING FAN CIRCUIT, PW/ST SIGNAL CIRCUIT, VEHICLE SPEED SEN CKT, IGN TIMING ADJ,
POWER BALANCE · ◐ FUEL PUMP CIRCUIT (`89`), START SIGNAL CIRCUIT (start bit), MIXTURE
RATIO TEST (O2 bank), IACV-AAC/V SYSTEM (`85`) · ☐ EGRC SOL/V CIRCUIT.

### DTC confirmation (EC-72): 20 items, 1 ◐ 19 ☐

- SRT STATUS: ◐, register `4E` looks like readiness bits (inferred).
- DTC WORK SUPPORT, 19 tests, all ☐: PURGE FLOW P1447, VC CUT/V BP/V P1491, PURG CN/V &
  S/V P1493, PURG VOL CN/V P1444, EVAP SML LEAK P0440 / P1440, FR O2 SEN-B1 P0130–P0133,
  FR O2 SEN-B2 P0150–P0153, RR O2 SENSOR P0137–P0139, EGR SYSTEM P0400 / P1402,
  EGRC-BPT/VLV P0402. Lead: the ROM's `0A` "direct mode" (first byte < `08`) loads
  stream lists in sets that match the FSM's test IDs (`ROM_ANALYSIS.md` §1).

## BCM / IVMS (`DA`)

The FSM gives the modes and systems (EL-168) but leaves the item lists to the CONSULT
operation manual, so items here are per system, plus the named items the trouble
diagnoses refer to.

### Modes (EL-168, EL-170, EL-220): 5 items, 1 ✅ 4 ☐

| Item | | Note |
|---|---|---|
| Part number (`D0`) | ✅ | |
| IVMS COMM DIAGNOSIS | ☐ | Needs a capture from a real CONSULT |
| WAKE-UP DIAGNOSIS | ☐ | Same |
| Door lock SELF-DIAG (cycles each motor) | ☐ | `D1` → `FE` |
| Erase IVMS memory (EL-170) | ☐ | `C1` untested |

### Data monitor: 12 systems, 0 ✅ 12 ◐

One `x2` item per system, all found and streaming; inputs mostly mapped in the `FF`
switch block, but the per-system items are barely decoded, so every system is ◐.

| System | Item | Decoded |
|---|---|---|
| Multi-remote | `02` | Remote shows only as a lock-state change |
| Power window | `12` | All switches + window lock (block bytes 12–13) |
| Door lock | `22` | Lock switch, lock state per door (byte 14) |
| Wiper | `52` | INT, washer, knob; speed switch open |
| Rear defogger | `62` | Defogger switch not located |
| Key warning | `72` | Key-in, driver door (bit 3) |
| Light warning | `82` | Lighting switch (bit 1), driver door (bit 3) |
| Room lamp | `92` | Doors |
| Seat belt | `B2` | Belt (bit 2) |
| Theft warning | `C2` | Doors, trunk, lock state; hood, key cylinder open |
| Step lamp | `E2` | Doors |
| Illumination | `F2` | Lighting switch (bit 1) |

Named DM items in the trouble diagnoses: IGN ON SW, IGN ACC SW, IGN KEY SW, LOCK SIG SW,
PW LOCK SIG. All five are located in the switch block (counted with their systems).

### Active tests: 18 outputs, 11 ✅ 5 ◐ 2 ☐

| Output | Bytes | |
|---|---|---|
| Trunk release | `03 03` | ✅ |
| Hazard | `03 04` / `C3 04` | ✅ |
| Panic | `03 06` | ✅ |
| P/W MOTOR (4 windows × up/down) | `13 01–08` | ✅ |
| Door locks (all) | `23 00` | ✅ |
| DR LOCK MTR (one door) | | ◐ (only all-doors found) |
| Wipers | `53 01` | ✅ |
| Rear defogger | `63 01` | ✅ |
| Room lamp | `93 01` | ✅ |
| Step lamps | `E3 01/02` | ✅ |
| ALARM RELAY (horn + headlamps) | `C3 01` | ✅ |
| Security indicator lamp | | ☐ |
| Starter interrupt | | ☐ |
| Illumination (rear P/W switch bulbs) | `F3`? | ◐ (no visible effect yet; try in the dark) |
| Key / light / seat-belt chime | `73` / `83` / `B3` | ◐ ◐ ◐ (all fire; mapping inferred) |

## Airbag (`DC`): 5 items, 1 ✅ 3 ◐ 1 ☐

| Item (RS-25) | Bytes | |
|---|---|---|
| ECU DISCRIMINATED NO. | `5A AC` = `6B` | ✅ |
| SELF-DIAG [CURRENT] | `D1` (6 bytes, `20…40`) | ◐ empty-list format inferred |
| SELF-DIAG [PAST] | `5A 8A/8B/9A/AB`? | ◐ which register is which: open |
| TROUBLE DIAG RECORD | same | ◐ |
| Erase [PAST] | | ☐ (don't hunt for it by probing) |

## ABS (`E7`): 24 items, 1 ✅ 23 ☐

Part number (`D0`) ✅. Everything else ☐: self-diag read and erase; data monitor
(FR RH / FR LH / RR RH / RR LH SENSOR, STOP LAMP SW, 8 solenoids IN/OUT SOL, ACTUATOR
RLY, MOTOR RELAY, WARNING LAMP, BATTERY VOLT = 16); active tests (4 solenoid pairs,
ABS MOTOR = 5). `9E 9F D1` go silent instead of `FE`, so it may want a longer request
or a different framing. **Active tests stay off-limits.**

## ASCD (unit not found): 22 items, all ☐

Self-diag (7): POWER SUPPLY-VALVE, VACUUM PUMP, AIR VALVE, RELEASE VALVE, VHCL
SP-S/FAILSAFE, CONTROL UNIT, BRAKE SW/STOP/L SW. Erase (1). Data monitor (14): BRAKE
SW, STOP LAMP SW, SET SW, RESUME/ACC SW, CANCEL SW, VHCL SPEED SE, SET VHCL SPD,
VACUUM PUMP, AIR VALVE, PW SUP-VALVE, CRUISE LAMP, A/T-OD CANCEL, FAIL SAFE-LOW,
FAIL SAFE-SPD. No active tests. Needs the init ID first (scan with MAIN on, KOER).

## Biggest wins left

| Step | Items it moves |
|---|---|
| Find the ASCD init ID | 22 items from 0 |
| Fire the inferred engine tests on the car (`80 81 82 85 89 8B 98`) | 7 ◐ → ✅ |
| Settle the O2 bank and `1E` bits | 7 ◐ → ✅ |
| Capture a real CONSULT on the BCM | IVMS COMM, WAKE-UP, door lock self-diag, erase |
| Paced / longer requests on `E7` (read-only) | ABS self-diag and data monitor (17) |
| Decode the `0A` direct mode | 19 DTC work support tests |
