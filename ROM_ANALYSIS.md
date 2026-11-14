# Engine ECU ROM analysis: 23710-2L904 (1998 Maxima VQ30DE, M/T)

Desk work on the ROM image read over Consult (`rom/23710-2L904_1000-FFFF.bin`, dumped
2026-11-14), cross-checked against the FSM (`fsm/EC.pdf`) and the car logs. CPU is
Mitsubishi M37702 (7700 family). Addresses are bank 0.

Confidence tags: **[ROM]** read directly from code or tables. **[ROM+car]** also matches
what the car did. **[inferred]** a reasoned guess, still to check on the car.

## 0. Tooling notes (read first)

- `tools/m7700dis.py` printed `SEB`, `CLB` and `LDM` operands in the wrong order:
  `1C 1C 07 20` showed as `CLB $2007,#$1C` but means "clear mask `$20` at `$071C`".
  The encoding is address first, immediate last. Fixed. Bit masks in `BBS`/`BBC` now
  print in hex too.
- Its built-in RAM labels were wrong (e.g. `$0994` was "battery_v", but it is the RPM
  LSB), and it named `$1300`/`$1400` "FUEL_MAP"/"TIMING_MAP" without evidence. Both
  removed.
- **`rom/23710-2L904.asm` is now generated** from the fixed tool plus the annotation file
  **`rom/23710-2L904.ann`** (labels, comments, RAM names, named tables). Edit the `.ann`
  and regenerate; don't hand-edit the listing:
  `python3 tools/m7700dis.py rom/23710-2L904_1000-FFFF.bin --ann rom/23710-2L904.ann -o rom/23710-2L904.asm`.
  Every called routine gets a "called from" line. The tool warns about annotations
  that don't land on an instruction or data start.
- The earlier hand-annotated listing (commit e2d9e28) had the operand bug, wrong RAM
  labels and several wrong roles (`D1` as "DTC clear", INT2 as "knock"). It is replaced.

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
| `02`/`03` | `$097A`/`$0979` | **Period of the 120° REF signal**, not RPM. Copied from captured timer value `$A8`. At 1175–1188 rpm, word × rpm = 2.49 M. A 120° signal with an 8 µs timer tick predicts exactly 2.5 M. So **rpm ≈ 2 500 000 / word**. [ROM+car, one RPM point only] |
| `04`/`05` | `$09D6`/`$09D5` | MAF, × 5 mV |
| `08` | `$0980` | Coolant, − 50 °C |
| `09` / `0A` | `$0B18` / `$0B36` | Front O2 sensors, × 10 mV. FSM: on the A32, **B1 = right bank, B2 = left bank** |
| `0B` | `$098B` | Vehicle speed, × 2 km/h |
| `0C` | `$09F4` | Battery, × 80 mV |
| `0D` | `$09F0` | TPS, × 20 mV |
| `10` | `$0895` | ? |
| `11` | `$0866` | Intake air temp, − 50 °C |
| `13` | `$072A` | Switch bits (see checklist 3.17) |
| `14`/`15` | `$0DAA`/`$0DA9` | Injection pulse, / 100 ms |
| `16` | `$0732` | Ignition timing, 110 − v |
| `18` | `$0BD9` | **IACV-AAC step**: written by the idle control routine (`$AC54`), which test `85` overrides. The FSM shows IACV-AAC in steps (spec 2–10 at idle), which is why `17` (%) is unsupported [ROM] |
| `1A`/`1B` | `$0730`/`$0731` | A/F alpha %. Active test `81` writes `$0730` |
| `1C`/`1D` | `$0B45`/`$0B5B` | Self-learn alpha % |
| `1E`/`1F`/`20` | `$0721–$0723` | Output bits |
| `21` | `$072B` | O2 rich/lean monitor bits |
| `22`/`23` | `$0DAC`/`$0DAB` | Injection pulse, other bank |
| `29` | `$0806` | **EVAP purge volume control valve step** [inferred, strong]: written by `$BD00`, overridden by test `98`, and `$9488` drives output ports from it. FSM spec: 0 step with the vehicle stopped |
| `28 2A 30 31 33–35 37–3A` | various | ? Candidates from the FSM data-monitor list: B/FUEL SCHDL, PURG VOL C/V, ENGINE MOUNT, CAL/LD, ABSOL TH-P/S, MASS AIRFLOW, EVAP SYS PRES, ABSOL PRES/SE, EGR TEMP, TANK F/TMP, RR O2 |
| `32` | `$0C4C` | Same RAM the freeze frame copies its load value from, so probably CAL/LD [inferred] |
| `3B–47`, `51` | `$05E0–$05ED` | **Freeze frame** (§3.2) |
| `56–5F` | `$0F70–$0F79` | **1st-trip freeze frame**, in backup RAM |
| `49 4A 4C 4E 4F 60 61` | various | ? |

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
| `21` | **P1320** | IGN SIGNAL-PRIMARY | 0201 | Known for ~1 year; came back 3 s after a clear. FSM causes: harness/connectors, the power transistor in each coil, **the condenser**, CKP (REF) sensor and circuit. Coils and plugs are already new. FSM condenser check: > 1 MΩ between its terminals at 25 °C (P1320 component inspection). |
| `34` | **P0325** | KNOCK SEN/CIRCUIT | 0304 | One-trip logic, no MIL, no freeze frame (FSM). Signal is ECM terminal 64, 2.0–3.0 V at idle. |
| `A8` | **P0443** | PURG VOLUME CONT/V | 1008 | EVAP canister purge volume control valve circuit. A 4-phase stepper on ECM terminals 26, 27, 110, 118 (EC-282). |

After the clear, `21` and `A8` came back as `F5`: 1st-trip (pending) codes, which is
why the MIL stayed off [ROM+car]. They become confirmed (MIL on) if detected again on
a later trip.

### 3.3 Freeze frame (`$DC62`)

When a fault confirms, the ECU writes the P-code to `$05E2` (registers `3B/3C`), then
copies load (`$0C4C`), `$0985`, `$0869/$086A`, fuel-trim values (`$0B5A`, `$0B44`,
`$0B2E` / 200) and a speed value into `$05E4–$05ED`. The FSM's freeze-frame item list
(fuel system status ×2, CAL/LD, coolant, short/long fuel trim ×2, RPM, speed) fits.
The exact order is still to confirm by reading `3B–47` on the car.

## 4. Active tests (`0A`), descriptor table at `$1160` [ROM]

Descriptor `(mask, ctl)`: `ctl >> 4` picks a flag byte `$07AC+n` (copied to `$07B7+n`
on `F0`). `(ctl & 7F) >> 1` is the value slot (`$076F + slot`). Every test takes a
value byte.

| Test | Flag | Value slot | Meaning |
|---|---|---|---|
| `80` | `$07B7.01` | `$076F` | Coolant temp override |
| `81` | `$07B7.02` | `$0770` | **Fuel injection**: clamped to `4B–7D` (75–125 %), written into alpha `$0730` |
| `82` | `$07B7.04` | `$0771` | Ignition timing |
| `85` | `$07B7.20` | `$0774` | **IACV-AAC opening**: forces register `18`, clamped to ≤ `81` steps [ROM] |
| `88` | `$07B8.01` | `$0777` | Power balance (cut cylinder 1 confirmed on car) |
| `89` | `$07B8.02` | `$0778` | Fuel pump relay |
| `8B` | `$07B8.08` | `$077A` | Self-learning clear |
| `8C` | `$07B8.10` | `$077B` | Forces an idle-air path (`$BC22`, constant `$22AF`). Unknown |
| `93`/`94` | `$07B9.08/.10` | `$0782/$0783` | Cooling fan low/high (car: fan ran) |
| `98` | `$07BA.01` | `$0787` | **PURG VOL CONT** [inferred, strong]: forces register `29`, clamped by a calibration limit (`$26BC`) |
| `95 99 9A 9C A2 A6 A7 AA AB AC AD` | | | Unknown (`A2` is on/off: zero vs non-zero). FSM tests left to place: EGRC SOLENOID, ENGINE MOUNTING, PURG VOL CONT, VENT CONTROL/V, VC BYPASS/V, PURG CONT S/V, MAP/BARO SW/V. Some IDs are probably A/T-only (shared firmware) |

- Test `83` has code (`$B39A`, clamped ≤ `90`), but no descriptor, so the ECU rejects it.
- Most test values are read by indexed code that the disassembler doesn't reach
  (≈ 14 % of `$3C00–$FFFF` is still undecoded), so the unknown IDs need more tracing.
- `30` during a test sets `$0F69.4` when `$07BC.04` (test `AA`) is active.

## 5. Interrupts (from what each handler writes)

| Vector | Handler | Role |
|---|---|---|
| INT2 | `$4797` | **Crank REF (120°) edge**: captures the REF period (registers `02/03`) and builds the coil-fire mask `$0A0C` [ROM]. The old listing called this "knock". |
| Timer A3 | `$4495` | Fires the coils in `$0A0C` [inferred] |
| Timer A2 | `$46C0` | Dispatches on event flags `$B9` (crank POS / timing events?) |
| UART0 TX | `$4BC2` | Used as the periodic **scheduler tick**: runs the task list (sensor reads, fuel, ignition, idle, diagnostics, `consult_task`) |
| UART1 RX + TX | `$4EF5` | Consult |
| Timer A4, B2, NMI | `$4540`, `$44B6`, `$473F` | Not verified |

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

- **P1320 (`21`, slot 8)** at `$E2F6`, run by the scheduler, with the monitor enabled
  by config bit `$120C.7`. It runs only with the engine running, the REF signal valid,
  past cranking or a timer, and load index `$09AE` ≥ 4. Every second call it samples
  **CPU input port P4 bit 3** (`$0A.3`). Each high reading counts a miss (and sets
  "seen this cycle"), and the count accumulates for as long as the preconditions hold.
  **10 misses → `dtc_detect(8)`** (1st trip; a second trip confirms). So an
  intermittent fault adds up across a drive. P4.3 is presumably the ignition-primary
  check line. Which ECM pin it is needs the board (the FSM lists no separate pin), and
  the FSM's causes (condenser, coil power transistors, harness) are what would drive it.
- **P0443 (`A8`, slot 79)** comes from the other CPU (§6) as `$0E55` bit 0. The logic
  isn't in this ROM.
- **P0325 (`34`, slot 19)**: the setter isn't found yet. It isn't a direct
  `dtc_detect` call, so it's probably also from the other CPU or in undecoded code.

## 8. Open questions

0. Read this CPU's own `$5D40–$623F` off the chip (Consult forwards that range, §1),
   and try `sub-dump` for the other CPU's memory.
1. Confirm `02/03` = REF period at a second RPM (e.g. 2500: expect word ≈ 1000).
2. Map registers `10 18 28–3A 49–4F 60 61` against the FSM data-monitor list (log them
   with the A/C, fan, purge and engine-mount states changing).
3. Name the 12 unknown active-test IDs (trace the indexed readers of `$076F+slot`).
4. Decode `D0` bytes 0–26.
5. What the `C9` remap of `$5D40–$623F` is for.
