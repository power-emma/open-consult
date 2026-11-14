# 1998 Maxima (A32): systems reference from the service manual

Digest of `fsm/*.pdf`, the **1998 Nissan Maxima** service manual (© 1997, confirmed by
`fsm/fwd.pdf` and GI; checklist 0.6). Page refs are the manual's printed numbers.
Full OCR text is in `reference/<SECTION>_ocr.txt`. The OCR is good for prose but
scrambles tables. For tables, render the page instead:
`pdftoppm -r 110 -gray -f N -l N -png fsm/EC.pdf out` (N = PDF page; the OCR files
mark them as `===== PDF page N =====`).

## 1. The car

- VQ30DE, firing order 1-2-3-4-5-6. Manual transaxle **RS5F50A** (RS5F50V with viscous
  LSD). (GI, quick reference chart)
- **Bank naming:** on the A32, **B1 = right bank, B2 = left bank** (EC-3, EC-67).
- Tune-up: idle **625 ± 50 rpm** (M/T, in N); ignition timing **15 ± 2° BTDC** at
  idle; plugs PFR5G-11, gap 1.0–1.1 mm; compression 1275 kPa (13.0 kg/cm²) standard,
  981 minimum, at 300 rpm.

## 2. Consult units on this car

| Init ID | Unit | Evidence |
|---|---|---|
| `ED` | Engine ECM 23710-2L904 | ROM hard-codes `ED`; `D0` matches label |
| `DA` | **BCM (IVMS) probably** | `D0` ends `2L900` = Nissan 28491-2L900 "Controller Assy-LAN" (97–99 Maxima). Was labelled ASCD from one silent attempt just after a key cycle; checklist 7.0 re-tests that |
| `DC` | **Airbag diagnosis sensor unit** | **Confirmed:** RS-25 says the A32 unit's "ECU DISCRIMINATED NO." is **6B**; `DC` register `AC` reads `6B` |
| `E7` | **ABS, confirmed** | `D0` ends `0L701` = Nissan 47850-0L701, the 95–99 Maxima VQ30DE anti-skid module |
| ? | ASCD (cruise) | Not found yet; scan with the ASCD MAIN switch on (checklist 7.0b) |

### Airbag (RS-25 … RS-39): what the blinking lamp meant

- Selecting AIR BAG on Consult **switches the unit from User mode to Diagnosis mode**.
  The AIR BAG lamp shows Diagnosis mode by flashing. BACK, or ignition OFF, returns it
  to User mode. So the 15:13 / 15:15 "incident" was most likely the normal mode switch,
  not damage. A key cycle restoring normal behaviour fits.
- Diagnosis-mode flash pattern 1 (a repeating uniform blink after 7 s) means **"a
  problem detected in the past is still stored (SELF-DIAG [PAST])"**. Patterns 2/3 show
  a part code. If the blink seen was pattern 1, the unit has a stored past record. User
  mode with the lamp on for ~7 s then off means no current fault.
- Consult modes: SELF-DIAG [CURRENT], SELF-DIAG [PAST] (erasable), TROUBLE DIAG RECORD
  (not erasable), ECU DISCRIMINATED NO.
- `DC` registers seen: `8A`(10), `8B`(5), `9A`(5), `AB`(25) were all `20`, which fits
  empty CURRENT/PAST/RECORD lists [inferred]. `AC` = `6B` is the discriminated number.
- No-tool entry: ignition ON, then press the driver's door switch 5 times within 7 s
  (only enters if a fault is present).
- **Keep it read-only.**

### ABS (BR-37 … BR-42)

- Consult: self-diag, data monitor (4 wheel sensors, stop lamp switch, 8 solenoids,
  valve relay, motor relay, battery) and **active tests that drive the solenoids and
  pump motor. Never send `0A` to `E7`.**
- Blink codes (ground the check terminal on the Consult connector): 12 = no fault, then
  the 3 latest codes:
  21/22 FR sensor open/short · 25/26 FL · 31/32 RR · 35/36 RL · 18 sensor rotor ·
  41/42 FR out/in solenoid · 45/46 FL · 51/52 RR · 55/56 RL · 61 motor or motor relay ·
  63 solenoid valve relay · 57 low supply voltage · 71 control unit.

## 3. Engine ECM

### 3.1 Consult reference values (EC-90 … EC-92)

| Item | Condition | Spec | Car (2026-11-14) |
|---|---|---|---|
| POS COUNT | running | 179–181 | — |
| MAF | warm idle / 2500 rpm | 1.0–1.7 V / 1.5–2.1 V | 1.09–1.13 / 1.75 ✓ |
| Coolant | warm | > 70 °C | 94 °C ✓ |
| Front O2 | 2000 rpm | 0–0.3 ↔ 0.6–1.0 V, > 5 switches per 10 s | switching ✓ |
| Battery | KOEO | 11–14 V | ✓ |
| TPS | closed / WOT (KOEO) | 0.35–0.65 V / ≈ 4.0 V | — |
| Injection pulse | idle / 2000 rpm | 2.4–3.2 / 1.9–2.8 ms | 2.57–2.67 / 2.39–2.45 ✓ |
| B/FUEL SCHDL | idle / 2000 | 1.0–1.6 / 0.7–1.3 ms | — |
| IGN TIMING | idle / 2000 | **15° BTDC** / > 25° | **7–13°** / 35° (check with a timing light) |
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
