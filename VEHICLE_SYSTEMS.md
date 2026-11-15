# 1998 Maxima (A32): systems reference from the service manual

Digest of the 1998 Nissan Maxima service manual (`fsm/*.pdf`). Page refs are the
manual's printed numbers. OCR text: `reference/<SECTION>_ocr.txt` (fine for prose,
scrambles tables). For tables, render the page:
`pdftoppm -r 110 -gray -f N -l N -png fsm/EC.pdf out`.

## 1. The car

| Item | Value | Source |
|---|---|---|
| Engine | VQ30DE, firing order 1-2-3-4-5-6 | GI |
| Banks | **B1 = right, B2 = left** | EC-3, EC-67 |
| Transaxle | RS5F50A, or **RS5F50V with viscous LSD** (this car) | MT-41 |
| Gears | 3.285 / 1.850 / 1.272 / 0.954 / 0.795, R 3.428 | MT-41 |
| Final drive | 3.823 (65/17), both transaxles | MT-41 |
| Tyres | P205/65R15 or P215/55R16 | GI |
| rpm per km/h | 5th 25.5, 4th 30.6, 3rd 40.85 (measured) | checklist 3.12 |
| Idle | 625 ± 50 rpm (M/T, neutral) | GI, EC |
| Ignition timing | 15 ± 2° BTDC at idle | GI, EC |
| Plugs | PFR5G-11, gap 1.0–1.1 mm | GI |
| Compression | 1275 kPa standard, 981 minimum, at 300 rpm | GI |

## 2. Consult units

| Init | Unit | Part / evidence |
|---|---|---|
| `ED` | Engine ECM | 23710-2L904 |
| `DA` | BCM (IVMS) | 28491-2L900 "Controller Assy-LAN". See [`BCM.md`](BCM.md) |
| `DC` | Airbag diagnosis sensor unit | Register `AC` = `6B`, the RS-25 "ECU DISCRIMINATED NO." |
| `E7` | ABS | 47850-0L701 |
| ? | ASCD (cruise) | Not found |

### Airbag (RS-25 … RS-39), read-only

| Item | Detail |
|---|---|
| Consult effect | Switches the unit from User mode to **Diagnosis mode**; the AIR BAG lamp flashes. BACK or ignition OFF returns to User mode |
| Flash pattern 1 | Uniform blink after 7 s = a past fault is stored (SELF-DIAG [PAST]) |
| Flash patterns 2/3 | Part code |
| Consult modes | SELF-DIAG [CURRENT], SELF-DIAG [PAST] (erasable), TROUBLE DIAG RECORD (not erasable), ECU DISCRIMINATED NO. |
| Registers | `8A` (10 B), `8B` (5), `9A` (5), `AB` (25): all `20` (empty lists, *inferred*). `AC` = `6B` |
| No-tool entry | Ignition ON, press the driver door switch 5 times within 7 s (only with a fault stored) |

### ABS (BR-37 … BR-42)

Consult offers self-diag, data monitor (4 wheel sensors, stop lamp switch, 8 solenoids,
valve relay, motor relay, battery) and **active tests that drive the solenoids and pump
motor: never send `0A` to `E7`.** Over this link only `D0` answers.

Blink codes (ground the check terminal): 12 = no fault, then the 3 latest codes.

| Code | Fault | Code | Fault |
|---|---|---|---|
| 21 / 22 | FR sensor open / short | 41 / 42 | FR solenoid out / in |
| 25 / 26 | FL sensor | 45 / 46 | FL solenoid |
| 31 / 32 | RR sensor | 51 / 52 | RR solenoid |
| 35 / 36 | RL sensor | 55 / 56 | RL solenoid |
| 18 | Sensor rotor | 61 | Motor or motor relay |
| 57 | Low supply voltage | 63 | Solenoid valve relay |
| 71 | Control unit | | |

## 3. Engine ECM

### 3.1 Consult reference values (EC-90 … EC-92)

| Item | Condition | Spec | Measured |
|---|---|---|---|
| POS COUNT | running | 179–181 | — |
| MAF | warm idle / 2500 rpm | 1.0–1.7 V / 1.5–2.1 V | 1.09–1.13 / 1.75 ✓ |
| Coolant | warm | > 70 °C | 94 °C ✓ |
| Front O2 | 2000 rpm | 0–0.3 ↔ 0.6–1.0 V, > 5 switches per 10 s | switching ✓ |
| Battery | KOEO | 11–14 V | ✓ |
| TPS | closed / WOT (KOEO) | 0.35–0.65 V / ≈ 4.0 V | KOER: 0.48 / 4.18–4.20 V |
| Injection pulse | idle / 2000 rpm | 2.4–3.2 / 1.9–2.8 ms | 2.57–2.67 / 2.39–2.45 ✓ |
| B/FUEL SCHDL | idle / 2000 | 1.0–1.6 / 0.7–1.3 ms | — |
| IGN TIMING | idle / 2000 | **15° BTDC** / > 25° | 5–15°, mostly 13° / 35–41° |
| IACV-AAC/V | idle | 2–10 **steps** | — |
| A/F alpha | 2000 rpm | 54–155 % | 102–107 % ✓ |
| CAL/LD | idle / 2500 | 14–33 % / 12–25 % | — |
| MASS AIRFLOW | idle / 2500 | 2–6 / 7–20 g/s | — |
| Cooling fan | warm idle, A/C off | OFF ≤ 94 °C, HIGH ≥ 105 °C | — |
| Front O2 heaters | idle / > 4000 rpm (M/T) | ON / OFF | — |
| ENGINE MOUNT | idle / 2000 | IDLE / TRVL | — |

### 3.2 Engine active tests the manual lists (EC-70 … EC-72)

FUEL INJECTION, IACV-AAC/V OPENING, ENG COOLANT TEMP, IGNITION TIMING, POWER BALANCE,
COOLING FAN, FUEL PUMP RELAY, EGRC SOLENOID VALVE, SELF-LEARNING CONT, ENGINE MOUNTING,
PURG VOL CONT, VENT CONTROL/V, VC BYPASS/V, PURG CONT S/V, MAP/BARO SW/V.
Byte mapping: `ROM_ANALYSIS.md` §4.

### 3.3 ECM terminals (EC-95 … EC-103, read from page images)

| Pin | Wire | Item | Pin | Wire | Item |
|---|---|---|---|---|---|
| 1 2 3 7 8 9 | Y/R G/R L/R GY PU/W GY/R | Ignition signal cyl 1–6 | 46 47 | W | CMP sensor (PHASE) |
| 4 | W/B | ECCS relay (self-shutoff) | 49 | W | CKP sensor (POS) |
| 5 | W/G | Tachometer | 50 / 51 | W | Front O2, right / left bank |
| 6 | R | A/T diagnosis signal | 52 | P/L | Tank fuel temp |
| 10 19 25 32 108 116 124 | B | ECCS ground | 54 / 55 | W / B | MAF signal / ground |
| 11 | B/P | Fuel pump relay | 56 | W | Rear O2 |
| 12 | B/R | A/C relay | 58 | SB | Intake air temp |
| 13 / 14 | LG / LG/R | Fan relay high / low | 59 | Y | Coolant temp |
| 16 | OR/Y | MAP/BARO switch solenoid | 61 | W | Absolute pressure sensor |
| 18 | LG/B | MIL | 62 | W | EVAP pressure sensor |
| 20 | BR/W | Start signal | 63 | L/OR | EGR temp |
| 21 | G/B | A/C switch | **64** | W | **Knock sensor** (2.0–3.0 V idle) |
| 22 | G/W | Neutral switch (M/T) | 65 66 73 74 77 | | A/T signals 4, 5, 1, 2, 3 |
| 23 / 37 | W / L/W | TPS / TPS signal | 67 72 | R | ECM power |
| 24 | R | Ignition switch | 69 | G/B | GST data link (6–10 V) |
| **26 27 110 118** | Y G G/B L/R | **EVAP purge volume control valve** (stepper) | 70 | OR/L | EVAP vent control valve |
| 29 | P/L | Vehicle speed sensor | **75 76 78** | BR/Y P LG | **Consult data link** |
| 31 | GY/L | Closed throttle switch | 79 | R/W | Electrical load (rear defogger) |
| 33 34 | W/L W/R | Front engine mount | 80 | W | Back-up power |
| 39 | G | Power steering switch | 101 115 122 123 | | IACV-AAC (stepper) |
| 42 / 43 | R / B | Sensor 5 V / ground | 102 109 104 111 106 113 | | Injectors 1–6 |
| 44 48 | W | CKP sensor (REF) | 103 | L/B | EGRC solenoid |
| | | | 107 | R | Rear O2 heater |
| | | | 114 | L/Y | Purge control solenoid |
| | | | 119 / 121 | L/Y / L | Front O2 heater right / left |
| | | | 120 | OR/G | Vacuum cut bypass valve |

### 3.4 Freeze frame (EC-43)

One set only: either freeze frame (2nd trip, MIL on) or 1st-trip freeze frame. Priority:
misfire and fuel-system codes, then everything else, then 1st-trip data. Items: fuel
system status, CAL/LD, coolant, short/long fuel trim, RPM, speed. Erased with the DTCs.

### 3.5 Stored codes on this car

See `ROM_ANALYSIS.md` §3.2: `21` = P1320 ignition signal, `34` = P0325 knock sensor,
`A8` = P0443 EVAP purge volume control valve circuit.
