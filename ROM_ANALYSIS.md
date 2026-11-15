# Engine ECU ROM analysis: 23710-2L904 (1998 Maxima VQ30DE, M/T)

ROM read over Consult (`rom/23710-2L904_1000-FFFF.bin`), cross-checked against the FSM
and the car. CPU: Mitsubishi 7700 family (M37702-like). Addresses are bank 0.

| Tag | Meaning |
|---|---|
| [ROM] | Read from code or tables |
| [ROM+car] | Also matches the car |
| [inferred] | Reasoned guess, unchecked |
| [PLMS] | From PLMS's 1999 A32 notes (ECU 23710-4L618, [PDF](https://www.plmsdevelopments.com/files/1999_a32_maxima_obd2_registers.pdf)); unchecked on this ECU |

**Listing:** `rom/23710-2L904.asm` is generated from `tools/m7700dis.py` and the
annotation file `rom/23710-2L904.ann`. Edit the `.ann`, then regenerate:
`python3 tools/m7700dis.py rom/23710-2L904_1000-FFFF.bin --ann rom/23710-2L904.ann -o rom/23710-2L904.asm`.

## 1. Consult handler (serial ISR `consult_isr`, `$4EF5`; reply builder `consult_task`, `$996A`) [ROM]

- **Init:** `FF FF` then only **`ED`** is accepted (`CMPB #$ED` at `$4FAE`). The reply
  is the complement, `12`. Any other ID byte drops back to waiting for `FF`. ECUTalk's
  `EF` never works on this ECU.
- **Accepted command bytes:** `FF` (re-init), `30` (stop), `C9` (memory read, 2 address
  bytes), `5A` (register, 1 byte), `0A` (active test), `D0`, `D1`, `C1`, and **`51`**.
  Anything else gets `FE` back. This matches the car (3.2: unsupported = `A5 FE`).
- **`51` is undocumented:** on `F0` it reports the "seen this ignition cycle" flags
  (`$0810–$0822`) as codes and clears them. It also zeroes test state (`$0E51–$0E57`,
  `$0E78–$0E7A`). Confirmed and pending codes are untouched, but avoid sending it
  until it has been tried on purpose.
- **`5A`:** register numbers `00–61` only (`CMPB #$62`). The RAM address comes from the
  pointer table at `$1000` (2 bytes per register, `$FFFF` = unsupported).
- **Request limit:** a new `5A`/`C9` is refused (`FE`) once the argument buffer
  (`$08D2`, counter `$073B`) holds `$28` = 40 bytes. `5A` stores 1 byte per register and
  `C9` 2 per address, so up to **40 registers** or 20 addresses per request. That is
  more than the usual "20 registers" (checklist 3.3), and untested on the car.
- **`0A <t> <v>`:** `t` in `80–AD` looks up a 2-byte descriptor at `$1160+2(t−80)`
  (§4). A first byte below `08` selects a separate "direct" mode that loads a stream
  list from tables at `$EA3F`/`$EA5B`. It is probably the OBD Mode 6 test results:
  the pointers come in sets that match the FSM's TID list. [inferred]
- **`C9` on `$5D40–$623F` is forwarded to the second processor (§6), so the ROM dump
  has a 1.25 KB hole.** For those addresses the reply builder (`$9AEB`) doesn't read
  this CPU's memory (nor `$FE00–$FFCF` when config bit `$1207.5` is set; it's clear
  here). `$543F` queues each one as address − `$5000`. The request goes to the other CPU
  through the shared RAM (`$024C/$024E`), and its answer (`$02B6` → `$07E7`) is put into
  the reply **one byte per frame, from the second frame on**. Our `rom-dump` read one
  frame per request, so **our dump of `$5D40–$623F` is stale reply bytes, not ROM**. It
  repeats the last good block, except for one varying byte per block, probably the
  other CPU's data. This CPU's own code there (the scheduler calls `$5F1B`) can only be
  read off the chip (checklist 11.2). The listing marks the range as a hole. `python -m
  consult sub-dump` streams each address to read the **other CPU's** `$0D40–$123F`
  (untested).
- **`D0`** returns the 32 bytes at ROM `$11C0` verbatim (they match the car byte for
  byte). The last 5 are ASCII `2L904`. The middle bytes are **not** a bitmap of
  supported registers or tests (checked). ASCII `J8ZM06` at `$FFCA` looks like the
  calibration ID.

## 2. Register map (`5A`), from the table at `$1000` [ROM]

73 supported registers, which is exactly the set the car scan found. Scalings are from
the car (checklist §3).

| Reg | RAM | Meaning |
|---|---|---|
| `00`/`01` | `$0995`/`$0994` | RPM, word × 12.5 [ROM+car] |
| `02`/`03` | `$097A`/`$0979` | **Period of the 120° REF signal**, not RPM. Copied from captured timer value `$A8`. At 1175–1188 rpm, word × rpm = 2.49 M; at 2400–2600 rpm, 2.50 M (word ≈ 1005). A 120° signal with an 8 µs timer tick predicts exactly 2.5 M. So **rpm ≈ 2 500 000 / word**. [ROM+car] |
| `04`/`05` | `$09D6`/`$09D5` | MAF, × 5 mV |
| `08` | `$0980` | Coolant, − 50 °C |
| `09` / `0A` | `$0B18` / `$0B36` | Front O2 sensors, × 10 mV. FSM: on the A32, **B1 = right bank, B2 = left bank** |
| `0B` | `$098B` | Vehicle speed, × 2 km/h |
| `0C` | `$09F4` | Battery, × 80 mV |
| `0D` | `$09F0` | TPS, × 20 mV |
| `10` | `$0895` | No bank-0 writer. EGR temperature sensor, × 20 mV [PLMS] |
| `11` | `$0866` | Intake air temp, − 50 °C |
| `13` | `$072A` | Switch bits (see checklist 3.17) |
| `14`/`15` | `$0DAA`/`$0DA9` | Injection pulse, / 100 ms |
| `16` | `$0732` | Ignition timing, 110 − v |
| `18` | `$0BD9` | **IACV-AAC step**: written by the idle control routine (`$AC54`), which test `85` overrides. The FSM shows IACV-AAC in steps (spec 2–10 at idle), which is why `17` (%) is unsupported [ROM] |
| `1A`/`1B` | `$0730`/`$0731` | A/F alpha %. Active test `81` writes `$0730` |
| `1C`/`1D` | `$0B45`/`$0B5B` | Self-learn alpha % |
| `1E` | `$0721` | Output image `$095C` & `C3` (`$9D3F`); the bits are set in bank 1 |
| `1F` | `$0722` | Port `$0C` bits 4–3 (`$9D47`) |
| `20` | `$0723` | b4 = `$07F1.1` |
| `21` | `$072B` | O2 monitor bits: b7 = `09` lean, b6 = `0A` lean (< ~450 mV); b0 latches on after warm-up [car] = `$0B81.6` and not `$0CD4.5`; b5/b4 = `$0E02.2/.1`. Built at `$8632` [ROM] |
| `22`/`23` | `$0DAC`/`$0DAB` | Injection pulse, other bank |
| `29` | `$0806` | **EVAP purge volume control valve step** [inferred, strong]: written by `$BD00`, overridden by test `98`, and `$9488` drives output ports from it. FSM spec: 0 step with the vehicle stopped |
| `33`/`34` | `$0ABE`/`$0ABD` | **CAL/LD**: `33` whole %, `34` fraction / 256 [PLMS]. Here the two registers are the two halves of one RAM word, and the fuel code multiplies by `$0ABD` (`MPY` at `$66CC`), which fits a load value |
| `35` | `$0B8A` | Rear O2, × 10 mV [PLMS] |
| `37` | `$09B4` | Absolute throttle position, % = v / 2.55 [PLMS]. Written at `$5849` after a filter |
| `38`/`39` | `$0A17`/`$0A16` | **One word: calibration `$26BB` × `$0A12`** (`$5558`), i.e. mass airflow. PLMS: `38` = % of the VQ table, × 272 / 100 g/s [ROM + PLMS] |
| `4A` | `$0D7A` | Absolute pressure sensor, × 20 mV [PLMS] |
| `28` | `$0DAD` | No bank-0 writer; next to the RH injector word `$0DAB/$0DAC` |
| `2A` | `$09F8` | No bank-0 writer; inside the ADC result block (`$09F0` TPS, `$09F4` battery), so a raw sensor value. Tank fuel temperature? [PLMS] |
| `30` | `$0724` | **Bits** (`$9D68`): b6 + b5 = `$095E.3` (one control bit, set together: front O2 heaters B1/B2? *(inferred)*), b4 = `$07F1.0`, b3 = NOT `$0E09.7`, b2 = `$095E.5` |
| `31` | `$072C` | **Bits** (`$8687`): b7 = switch input `$092B.6` (the bit register `13` masks out), b1 = NOT `$0213.1` (second CPU) |
| `3A` | `$0872` | No bank-0 writer. The `AB` monitor range-checks it (`$2BDB–$2BDC`), so EVAP-related *(inferred)* |
| `32` | `$0C4C` | **A 00/FF flag, not CAL/LD**: `$DD8A` writes `FF` or `00` from a comparison of the MAF word with calibration value `$22FB`. (The freeze frame does copy it.) Meaning open [ROM] |
| `3B–47`, `51` | `$05E0–$05ED` | **Freeze frame** (§3.2) |
| `56–5F` | `$0F70–$0F79` | **1st-trip freeze frame**, in backup RAM |
| `49` | `$0725` | **Bits** (`$9D89`): **MAP/BARO switch solenoid** `$095E.1` (b3 = on, b5 = off; toggled by `$E7A2`, which samples the pressure sensor in each state), b2 = `$095D.2` (test `A2` output), b0 = `$0961.0` |
| `4C` | `$07FA` | From the second CPU's message block (`mb_in` + `18`, `$C867`) |
| `4E` | `$0726` | **Bits** (`$9DA7`) from backup-RAM monitor flags `$0F66`/`$0F68`: monitor-complete / readiness status *(inferred)* |
| `4F` | `$072F` | **Bits** (`$9DEF`): b1 from `$0F69.7`, `$0F66.0` and REF valid |
| `60` | `$0D24` | No bank-0 writer |
| `61` | `$0F6D` | Backup RAM: step of the `AB` monitor sequence (table `$9913`, `$990F`) |

## 3. Fault codes [ROM+car]

### 3.1 How codes are stored

- 152 fault slots, each a bit in five 19-byte arrays (bit `$80` first):

  | Array | Meaning | Set by |
  |---|---|---|
  | `$0580` | **1st-trip (pending)** | `dtc_detect` (`$DE86`) on the first trip |
  | `$05A0` | **Confirmed** (MIL) | `dtc_confirm` (`$D371`) on the 2nd trip |
  | `$05C0` | Confirmed at some point (history) | `dtc_confirm` |
  | `$0810` | Detected this ignition cycle | both |
  | `$0830` | 1st-trip already handled this cycle | `dtc_detect` |

- **`D1`/`C1` reply** (`$99DF`): confirmed codes first, each with its starts counter
  (a code drops out of the reply once its counter reaches 40), then **1st-trip codes,
  each with the starts byte hard-coded `F5`**. No codes gives `55 00`. This confirms
  the "`F5` = pending" reading from checklist 2.6. **`C1`** builds the same reply and
  only then requests the clear, so the reply shows the codes as they were before the
  clear (as seen on the car).
- Slot *i* is reported by `D1` as the byte at **`$9E0E + i`**. That table simply runs
  `11–18, 21–28, … E1–E8, 19–1F, 10, 29–2F, 20, …`, so the code byte is an index, not
  a Nissan code number.
- Slot *i*'s OBD-II code is the BCD word at **`$E086 + 2i`** (e.g. `04 43` = P0443).
  Pointers to per-slot counters are at `$E1C6 + 2i`.
- 123 slots have a P-code. **All 86 DTCs in the FSM index are among them**, which
  checks the mapping. The other 37 are generic slots this firmware shares with other
  Nissan engines (P0235 turbo, P0307/P0308, …).
- `consult/dtcs.py` and `src/registers.c` are generated from these tables plus the FSM
  names. The script is reproducible: read the two tables and join on *i*.

### 3.2 This car's codes, decoded

| `D1` byte | P-code | FSM name | ECM Mode II code | Notes |
|---|---|---|---|---|
| `21` | **P1320** | IGN SIGNAL-PRIMARY | 0201 | Returns within seconds of a clear. FSM causes: harness/connectors, coil power transistors, **condenser** (> 1 MΩ across its terminals at 25 °C), CKP (REF) sensor and circuit |
| `34` | **P0325** | KNOCK SEN/CIRCUIT | 0304 | One-trip logic, no MIL, no freeze frame (FSM). Signal is ECM terminal 64, 2.0–3.0 V at idle. |
| `A8` | **P0443** | PURG VOLUME CONT/V | 1008 | EVAP canister purge volume control valve circuit. A 4-phase stepper on ECM terminals 26, 27, 110, 118 (EC-282). |

After a clear, `21` and `A8` return with starts byte `F5`: 1st-trip (pending), MIL off
[ROM+car]. A detection on a later trip confirms them.

### 3.3 Freeze frame (`$DC62`)

When a fault confirms, the ECU writes the P-code to `$05E2` (registers `3B/3C`), then
copies `$0C4C` (first read as load; it is a 00/FF flag, §2), `$0985`, `$0869/$086A`, fuel-trim values (`$0B5A`, `$0B44`,
`$0B2E` / 200) and a speed value into `$05E4–$05ED`. The FSM's freeze-frame item list
(fuel system status ×2, CAL/LD, coolant, short/long fuel trim ×2, RPM, speed) fits.
The exact order is still to confirm by reading `3B–47` on the car.

## 4. Active tests (`0A`), descriptor table at `$1160` [ROM]

Descriptor `(mask, ctl)`: `ctl >> 4` picks a flag byte `$07AC+n` (copied to `$07B7+n`
on `F0`). `(ctl & 7F) >> 1` is the value slot (`$076F + slot`). Every test takes a
value byte. Any running test sets `$07F1.2` (sent to the second CPU). Handlers marked
"bank 1" aren't readable over Consult (§8).

| Test | Flag | Value | Handler | Meaning |
|---|---|---|---|---|
| `80` | `$07B7.01` | `$076F` | bank 1 | Coolant temp override |
| `81` | `$07B7.02` | `$0770` | `$6E15`, `$7434` | **Fuel injection**: clamped `4B–7D` (75–125 %), written into alpha `$0730` |
| `82` | `$07B7.04` | `$0771` | bank 1 | Ignition timing |
| `85` | `$07B7.20` | `$0774` | `$ACB3` | **IACV-AAC opening**: forces register `18`, ≤ `81` steps |
| `88` | `$07B8.01` | `$0777` | bank 1 | Power balance (cylinder 1 cut on the car) |
| `89` | `$07B8.02` | `$0778` | bank 1 | Fuel pump relay |
| `8B` | `$07B8.08` | `$077A` | bank 1 | Self-learning clear |
| `8C` | `$07B8.10` | `$077B` | `$ACA0` | Forces an idle-air path (`$BC22`, constant `$22AF`) |
| `93` / `94` | `$07B9.08/.10` | `$0782/3` | bank 1 | Cooling fan low / high (fan ran on the car). Use as a pair |
| `95` | `$07B9.20` | `$0784` | bank 1 | ? |
| `98` | `$07BA.01` | `$0787` | `$BFB3`, `$7384` | **PURG VOL CONT** *(inferred, strong)*: forces register `29`, limit `$26BC` |
| `99` | `$07BA.02` | `$0788` | bank 1 | ? |
| `9A` | `$07BA.04` | `$0789` | bank 1 | Canister vent control valve [PLMS] |
| `9C` | `$07BA.10` | `$078B` | bank 1 | Vacuum cut bypass valve [PLMS] |
| `A2` | `$07BB.04` | `$0791` | `$F4C0` | On/off (value 0 / non-0): forces output bit `$095D.2` in task `$F468`, which otherwise switches it on throttle (`37`) and speed thresholds `$2BBC–$2BBE`. Engine mount? *(inferred, weak)* |
| `A6` | `$07BB.40` | `$0795` | bank 1 | ? |
| `A7` | `$07BB.80` | `$0796` | bank 1 | Vacuum cut bypass valve [PLMS] |
| `AA` | `$07BC.04` | `$0799` | `$5406` | **Persistent side effect:** stopping it sets backup-RAM `$0F69.4`, which stops the session reset (`$550A`) from clearing `$0F69` bits 7–6. Bit 7 gates logic at `$9DEF`. Avoid |
| `AB` | `$07BC.08` | `$079A` | `$98BB`, `$992E` | Drives a backup-RAM monitor sequence (`$0F6C–$0F6E`, uses register `3A`); canister vent valve [PLMS] |
| `AC` | `$07BC.10` | `$079B` | bank 1 | ? |
| `AD` | `$07BC.20` | `$079C` | bank 1 | ? |

- `$511D` rejects tests outside `80`–`AD`. **Don't fire unknown tests**: on a 1999 ECU
  one above `9F` re-registered the NATS keys [PLMS].
- Fans [PLMS]: low = `93 01` + `94 00`, high = `93 00` + `94 01`. Both `01`: avoid.
- `83` has code (`$B39A`) but no descriptor, so it's rejected.

## 5. Interrupts (from what each handler writes)

| Vector | Handler | Role |
|---|---|---|
| INT2 | `$4797` | **Crank REF (120°) edge**: captures the REF period (registers `02/03`) and builds the coil-fire mask `$0A0C` [ROM]. The old listing called this "knock". |
| Timer A3 | `$4495` | Fires the coils in `$0A0C` [inferred] |
| Timer A2 | `$46C0` | Dispatches on event flags `$B9` (crank POS / timing events?) |
| UART0 TX | `$4BC2` | Used as the periodic **scheduler tick**: runs the task list (sensor reads, fuel, ignition, idle, diagnostics, `consult_task`) |
| UART1 RX + TX | `$4EF5` | Consult |
| Timer A4, B2 | `$4540`, `$44B6` | **Knock interface chip**: per-cylinder values to `$030266`; B2 also runs the chip watchdog (§8b) |
| NMI | `$473F` | Not verified |

The Consult code uses registers `$32/$35/$36` (data out, status, data in) and `$F0/$F1`
(enables). That doesn't fit the stock M37702 register map, so the exact chip variant
is unconfirmed; read the markings when the ECU is out (checklist 11.3).

## 6. Second processor and the shared RAM at `$0200–$02FF` [ROM]

This ECU has a second CPU (or another bus master), linked by an 8-bit shared RAM at
`$0200–$02FF`. Every access uses either even or odd addresses only, which fits an
8-bit chip on one byte lane. Nothing in this ROM writes the incoming half, but the
code reads it constantly.

- **Outgoing** (`obd_task`, `$CC52`): RPM, load, trims, purge step, timing, CAL/LD,
  speed, battery, switch/output bits and the pending `C9` address, written to
  `$0202, $0204, … $025E`. `$029E` is the handshake: `A5` means the other side is ready.
- **Incoming:** `$02A0–$02FE`, picked up by `$C7F5` according to the message type in
  `$029E & 7`. Type 0 carries the **fault-detection flags `$0E51–$0E58`**, which
  `$D1E8`/`$D237` turn into `dtc_detect` calls. Those cover slots 48–95 (misfire
  P0300–P0306, catalyst, EVAP, **P0443**, A/T…) and, through `$0E58`, front O2, EGR,
  IAT and others. Other types fill values such as `$088E–$0892` and `$0829–$082B`.
- **So many OBD-II monitors, including the one that set P0443, run on the other CPU**,
  whose code we don't have. It probably also handles the GST (OBD-II) line on ECM pin
  69 [inferred]. Its memory should be readable through the `C9` forward (§1).
- The write-only window `$38xx–$3Bxx` (143 writes, no reads) gets copies of DTC,
  freeze-frame and `C9` request values. It may be a second output path or a debug
  port [unknown].

## 7. How this car's codes are detected

- **P1320 (`21`, slot 8)** at `$E2F6` [ROM+car]: fixed-rate slow task (`$4C69`), not
  synced to ignition. Enabled by `$120C.7`.

  | Step | Code | Detail |
  |---|---|---|
  | Preconditions | `$E2F6–$E328` | `$0850.0`, not `$07EE.5`, REF valid (`$092A.6`, `$0931.2`), past start or `$0ACA` ≥ 30, load `$09AE` ≥ 4. Else count = 0 |
  | Spacing | `$0C6F` | Sample needs ≥ 2; a miss resets it. ≤ 1 miss per 2 calls |
  | Sample | `$E331` | P4.3 (`$0A.3`) high = miss |
  | Count | `$0C60` | +1 per miss, sets `$0811.7` |
  | Detect | `$E341` | At 10: `dtc_detect(8)`, count back to 0 |

  | Drive (655 s) | |
  |---|---|
  | Detections | 2–5 per second; never 0.15 s without a miss |
  | Misses | 18–20/s idle, 42–48/s under load (near the ceiling) |
  | P4.3 high | 36 % at `$09AE` 32–63, 92 % at ≥ 224; 0 KOEO |

  P4.3 has no FSM wire of its own (EC-331 … 333); presumably an internal check on the
  six coil outputs (pins 1 2 3 7 8 9) [inferred]. All cylinders fire, so the *check*
  fails. A ~11 ms window per spark on every cylinder fits the numbers, which points at a
  shared cause: condenser, coil supply or ground, coil type, or the ECM [inferred].
- **P0325 (`34`, slot 19)**: not set in bank 0; probably by the second CPU, which gets
  knock-chip timeouts via `$0235` (§8b) [inferred].

## 8. Calibration maps [ROM + PLMS]

Same layout as PLMS's 1999 ECU: every address holds the table PLMS names. The code
that reads them isn't traced (no direct operands or pointers found).

| Address | Size | Table | What our ROM shows there |
|---|---|---|---|
| `$1220` | 128 | VQ (MAF voltage → flow) | Rising 16-bit words `0003 000E 0021 003D …` |
| `$1400` | 16×16 | Volumetric efficiency | First row `7A`–`7D` |
| `$1500` / `$1510` | 16 | VE load / rpm scale | `08 10 … 80` / `10 20 … FF` |
| `$1700` | 16×16 | Fuel map | `80` (= 100 %?) rising to `AE` |
| `$1800` | 16×16 | **Knock** fuel map | Same shape, lower at high load (row 15: `A5` vs `AE`) |
| `$1900` / `$1910` | 16 | Fuel load / rpm scale | `08 10 … 80` |
| `$19A0` | 16 | After-start enrichment vs temperature | `6F 6F 55 42 32 … 0B`, falls with temperature |
| `$19C0` | 16 | Cold-start enrichment vs temperature | `58 … 48` |
| `$1D00` | 16×16 | **Ignition timing** | Rows 9–15: plain degrees, 48° falling to 13° across the row. Rows 1–8, columns 7–15: bit 7 set, low 7 bits plausible degrees (`9E` → 30°); the flag's meaning is open |
| `$1E00` | 16×16 | **Knock** timing map | Same, but up to ~9° lower in most high-load cells (161 of 256 cells lower) |
| `$1F00` / `$1F10` | 16 | Timing rpm / load scale | `08 10 … 40 44 48 …` / `08 10 … 80` |

Row/column axes need the lookup code. Measured WOT timing to compare against: 9–10°
at 3750–4500 rpm, 15–16° above 5000 (checklist 3.14).

**Bank 1:** the firmware calls 24 routines at `$01xxxx` (e.g. `$4C96 $4CEE $4CF2 $4D20
$4D52`). `C9` takes 16-bit addresses, so they need a chip read. Nothing in bank 0 points
at the 2D maps, so their lookups are there. 1D lookups (`interp8/16/32`, `$EA77`) are in
bank 0.

Timing path in bank 0 (INT2, `$47A8`):

| Term | RAM | Source |
|---|---|---|
| Base timing | `$0BA6` | Set only at reset in bank 0; the map value from bank 1 [inferred] |
| Knock retard | `$0DB7/$0DB8` | §8b. Ignored if `$28AC` ≠ 0 (here `00`) |
| Correction | `$0E01` | `$A9B9`, from `$0DFC` and the knock retard |
| Correction | `$096D` | `interp8` of table `$2270` by `$09B0`, only under conditions (`$5694`) |
| Limits | `$20D7/$20D8`, `$20D4` | Clamp, then target `$0BA8` = `$20D4` − sum, clamped `30–75` |
| Rate limit | `$0BA9` | Steps toward `$0BA8` by at most `$0BAA` (advance) / `$20D5` (retard) |
| Per-cylinder | `$0DB0–$0DB5` | Subtracted per cylinder; register `16` = `$0BA9` − trim + `80` (`$4928`) |


## 8b. Knock control [ROM]


| Part | Where | Detail |
|---|---|---|
| Knock interface chip | bank 3 I/O: `$030262` control, `$030266` data | Programmed per cylinder from the Timer A4 / B2 interrupts (`$4545`, `$44C4`). Self-test handshake at `$9EDA`: reads `CC00` → chip OK (`$0DD0.0`, `.6`); `AA55` → reply `55AA` |
| Per-cylinder values | 6 × 16-word tables `$26F0–$2790` (normal), `$27B0–$2850` (alternate) | Indexed by `$09AC` (rpm-related) into `$0DE1–$0DEB`, sent to the chip per cylinder (`$4579`). `FFFF` outside the active rpm band. Alternate set is flat (`0025–0028`) and used when `$0DCF.3` is set |
| Chip watchdog | Timer B2, `$44E8` | If the second CPU's `$021F.3` doesn't toggle for `$239F` interrupts: clear `$0DD0.0` (chip not OK), pulse `$0710.0` → `$0235` to the second CPU, count in `$0DE0` |
| Knock status | `$0213.3` (from the second CPU) | 1 = knock system OK |
| Active zone | `$9F27–$9FA8` | Coolant ≥ `$2883` (60 °C), REF valid, not cranking, rpm index `$09B1` ≥ `$2881`, CAL/LD `$0ABE` ≥ `$2882` (56 %), with hysteresis. Outside it the retard is cleared |
| Retard | `$0DC1` → `$0DB7/8` | `$2884` per knock event (`$0DC7` = count from the interrupt); learned separately below / above rpm index `$2880` (`$0DB9`, `$0DBB`); slewed by `$288E`; clamped to `$0DD1/$0DD3` |
| **Fail-safe** | `$9FBC–$9FE2` | If `$0213.3` = 0 (or `$0DD0.7`): latch `$070D.7`, set **fixed retard `$2895` = `FC`** (−4 counts, i.e. 4° less advance in register-16 units *(inferred)*), set `$0DCF.3` (alternate tables) |

**This car (P0325 stored):** probably in fail-safe, ~4° fixed retard [inferred]. Check:
`python -m consult knock`.

## 9. Open questions

1. P1320 (§7): `python -m consult p1320` while unplugging one coil at a time. Test the
   condenser by capacitance.
2. Knock fail-safe state (§8b): `python -m consult knock`.
3. Chip read: bank 1 (maps, test handlers) and `$5D40–$623F`.
4. Dump the second CPU with `sub-dump`.
5. Confirm the [PLMS] scalings on a drive; name `28 2A 3A 60`.
6. Unknown active tests `95 99 A6 AC AD` (bank 1). Don't fire them.
7. Decode `D0` bytes 0–26.
