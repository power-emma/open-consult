# Plan: Body-Electrical (IVMS / ASCD / Airbag) Diagnostics over Consult

This plan is based on `EL.pdf`, the Electrical System section of the service manual.
The PDF is scanned images, so I OCR'd it into `reference/EL_ocr.txt`. EL page numbers
below are the manual's printed `EL-nnn` numbers.

> ⚠ The OCR text does not name the model or year. Check the cover or title page of
> `EL.pdf` to confirm it is the 1998 Maxima manual before trusting any item list here.

---

## 1. What the manual tells us

### 1.1 The car has more than one Consult-capable control unit

The CONSULT "SELECT SYSTEM" screen in the manual (EL-99, 113, 169, 219, 280, 285)
lists **ENGINE, A/T, AIRBAG, IVMS** plus **ASCD** (cruise control, EL-150). Each is a
separate control unit reached through the same Consult data-link connector.

Our protocol notes (`CONSULT_PROTOCOL.md` §10) say the third init byte selects the
unit: `FF FF EF` = engine, `EA` = A/T, `E4` = HICAS, `DF` = auto A/C. **The init bytes
for IVMS (BCM), ASCD and AIRBAG are not documented anywhere I found.** Finding them is
step one.

> Useful pattern: the engine answers init `EF` with `10`, and `10` = `~EF`. The reply
> is probably the bitwise complement of the address byte, the same echo rule as
> commands. If so, a scanner can recognise a hit without knowing the unit in advance.
> ⚠ This is a hypothesis to confirm on the A/T unit (`EA` → expect `15`).

### 1.2 IVMS: In-Vehicle Multiplexing System (EL-164 … EL-197)

- **BCM (Body Control Module)** is the master. It talks to 5 **LCUs** (Local Control
  Units) over two multiplex data lines, A-1 and A-2:
  - LCU01: driver door
  - LCU02: passenger door
  - LCU03: rear RH door
  - LCU04: rear LH door
  - LCU05: multi-remote (keyless entry)
- Consult talks to the **BCM only**. The BCM reports on the LCUs.
- Note on EL-168: *"When CONSULT diagnosis is operating, some systems under IVMS control
  do not operate."* Expect side effects while connected. For example, the intermittent
  wiper stops during Data Monitor (EL-101).

### 1.3 CONSULT functions per IVMS "test item" (EL-168 table)

| Test item | Self-diag | Data monitor | Active test | Notes |
|---|:-:|:-:|:-:|---|
| IVMS-COMM CHECK | ✓ | | | Two special modes: **IVMS COMM DIAGNOSIS** and **WAKE-UP DIAGNOSIS** |
| POWER WINDOW | | ✓ | ✓ | |
| DOOR LOCK | ✓ | ✓ | ✓ | EL-219 |
| MULTI-REMOTE CONT SYS | | ✓ | ✓ | |
| THEFT WARNING SYSTEM | | ✓ | ✓ | |
| ROOM LAMP TIMER | | ✓ | ✓ | EL-285 |
| STEP LAMP | | ✓ | ✓ | |
| ILLUM LAMP | | ✓ | ✓ | EL-280 |
| IGN KEY WARN ALM | | ✓ | ✓ | buzzer |
| LIGHT WARN ALM | | ✓ | ✓ | buzzer |
| SEAT BELT TIMER | | ✓ | ✓ | buzzer |
| WIPER | | ✓ | ✓ | EL-99 |
| REAR DEFOGGER | | ✓ | ✓ | EL-113 |

(The OCR of this table is a bit garbled. The ✓ marks follow each section's "…are
available for…" sentence where one exists.)

### 1.4 Item catalogue found in the manual (OCR'd names, may have small typos)

**BCM data monitor (switch inputs):**
`IGN ON SW`, `IGN ACC SW`, `IGN KEY SW`, `HD/LMP 1ST SW`, `SEAT BELT SW`, `DOOR SW-DR`,
`DOOR SW-AS`, `DOOR SW` (all doors), `HOOD SWITCH`, `TRUNK SWITCH`, `TRUNK UNLK SW`,
`TAMPER SW-TRK`, `TRUNK BTN-CON`, `INT SW`, `WASH SW`, `DEFOGGER SW`, `VHCL SPEED SE`,
`LOCK SIG-DR`, `DOOR LK SW-LK`, `DOOR LK SW-UN`, `KEY CYL LK-DR`, `KEY CYL LK-AS`,
`KEY CYL UN-AS`, power-window switches (`P/W SW DR-AUT`, `…DR-DWN`, `…AS-UP/DWN`,
`…RL-UP/DWN`, `MAIN SW AS-UP`, `MAIN SW RL-UP`, `MAIN SW RR-DWN`, …).

**BCM analog values:** `INT RESIST` (intermittent wiper knob, kΩ: 0 = short interval,
≈1 = long; shown as `0.784K`). It is the only non-boolean BCM value seen. It suggests
data comes back as raw bytes the tool scales, the same as engine registers.

**BCM active tests:** `WIPER AMP`, `LIGHT WARN ALM`, `IGN KEY WARN ALM`,
`SEAT BELT WARN ALM`, `HAZARD`, `RR DEFOGGER RLY`, `DR LOCK MTR-DRVR` (and the other
doors), `ALARM RELAY`, `INTERRUPT RELAY` (starter interrupt), security `INDICATOR LAMP`,
interior/step/illumination lamps, power windows.

**IVMS communication diagnosis results (EL-172 … 174):** each unit
(`POWER WINDOW C/U-DR`, `-AS`, `-RR`, `-RL`, `MULTI-REMOTE`, `BCM`) can show one of
`NO FAILURE`, `[COMM FAIL]`, `[NO RESPONSE]`, `[SLEEP]`, `[PAST COMM FAIL]` or
`[PAST NO RESPONSE]`. The matching on-board blink codes are:

| Unit | COMM FAIL | NO RESPONSE |
|---|---|---|
| LCU01 driver door | 24 | 25 |
| LCU02 passenger door | 34 | 35 |
| LCU03 rear RH | 41 | 42 |
| LCU04 rear LH | 44 | 45 |
| LCU05 multi-remote | 54 | 55 |
| none | 11 = no malfunction | |

**Door lock self-diag (EL-221):** `DOOR LOCK MOTOR-DR`, `-AS`, `-RR/RH`, `-RR/LH`
(actuator or unlock-sensor circuit), `NO SELF DIAGNOSTIC FAILURE INDICATED`.

**Erase memory:** CONSULT can erase stored IVMS results (EL-170). The manual's
fallback is pulling the 7.5 A fuse.

### 1.5 ASCD cruise control unit (EL-150, 151)

- **Precondition:** the ASCD main switch must be ON.
- **Self-diag:** `POWER SUPPLY-VALVE`, `VACUUM PUMP`, `AIR VALVE`, `RELEASE VALVE`,
  `VHCL SP-S/FAILSAFE`, `CONTROL UNIT`, `BRAKE SW/STOP/L SW`, and the
  `NO SELF DIAGNOSTIC FAILURE INDICATED` message.
- **Data monitor:**
  - Switches: `BRAKE SW`, `STOP LAMP SW`, `SET SW`, `RESUME/ACC SW`, `CANCEL SW`
  - Speeds (mph): `VHCL SPEED SE`, `SET VHCL SPD`
  - Times (msec): `VACUUM PUMP`, `AIR VALVE`
  - States: `PW SUP-VALVE`, `CRUISE LAMP`, `A/T-OD CANCEL`, `FAIL SAFE-LOW`, `FAIL SAFE-SPD`
- **No active test** listed.

### 1.6 On-board diagnosis without Consult (EL-175 … 179)

The BCM has blink-code modes that need no tool:

| Mode | What it does | Page |
|---|---|---|
| I | Communication diagnosis | EL-176 |
| II | Switch monitor: every switch press gives a lamp blink + buzzer | EL-178 |
| III | Door-lock self-diag | EL-222 |
| IV | Power-window monitor | EL-205 |

Entry for Mode II is described in the manual. **This is our ground truth.** Whatever we
decode over Consult can be checked against these modes, and Mode II tells us which
switches the BCM can see.

### 1.7 What the manual does *not* give us

The manual gives no bytes, init addresses, register numbers or bit positions. It says
*"read the CONSULT Operation Manual"* for details. We have to reverse-engineer the
mapping from item names to bytes.

---

## 2. Strategy

We are mapping known *names* (from §1) to unknown *bytes*. Do it in order from safest
to riskiest:

1. **Find the units** (init scan). Read-only and harmless.
2. **Identify each unit** (`D0`) and **read self-diag** (`D1`). Read-only.
3. **Map data-monitor registers** (`5A` probing + differential logging). Read-only.
4. **Try "stream all"** (`9F`), which A/T and HICAS units use. Read-only.
5. **Get ground truth from a real tool if at all possible** (sniff a genuine Nissan
   CONSULT or another tool that supports IVMS/ASCD).
6. **ROM dump** (`C9`) of the BCM/ASCD if they allow it. Disassembly gives the full
   command table.
7. **Active tests** only after 3–6, starting with the most benign outputs.
8. **IVMS COMM / WAKE-UP diagnosis and erase memory**: these are likely special
   commands. Leave them for sniffing or disassembly.

---

## 3. Phases in detail

### Phase 0: Tooling prerequisites (do first)

- [ ] A **raw transport + logger** in the project: every byte TX/RX, timestamped,
      written to a `.jsonl`/hex log. All later phases depend on replayable logs.
- [ ] A **`probe` CLI** with sub-commands: `scan-init`, `id`, `dtc`, `reg-scan`,
      `reg-watch`, `stream-all`, `rom-dump`. Each has timeouts and always sends `30`
      and drains on exit.
- [ ] A **unit profile format** (YAML/JSON) holding the init byte, supported commands,
      registers {addr, name, size, scale, unit, bit map} and active tests. The engine
      profile from `CONSULT_PROTOCOL.md` is the first one.
- [ ] Turn the §1.4–1.5 catalogue into `profiles/_catalogue_el.yaml`, with names only
      and `addr: null`. Fill in addresses as they are discovered.

### Phase 1: Bus discovery, find the init byte for each unit

Conditions: ignition ON, engine OFF, battery charger connected (the car will sit at
ignition ON for a long time).

```
for x in 0x00..0xFF:
    send 30, drain 200 ms          # reset any unit left talking
    send FF FF x
    read for ~500 ms, log everything
    if reply == ~x (or any byte): mark candidate, then send 30 and drain
```

- Expect hits at `EF` (engine) and probably `EA` (A/T). Any **new** hit is the BCM, ASCD
  or airbag unit.
- Tell them apart by:
  - `D0` part numbers. Nissan part prefixes: 23710 = engine ECU, 31036 = A/T,
    284B1/28551 ≈ BCM, 98820 = airbag. ⚠ Prefixes are from general knowledge; verify
    against the labels.
  - Pulling one fuse at a time. The unit that disappears is on that fuse; the EL power
    routing pages show which fuse feeds which unit.
  - Turning the ASCD main switch ON/OFF. The ASCD unit should only answer with it ON.
- Re-run the scan with the engine running and with the ASCD switch on. Units can be
  asleep. The BCM especially has sleep/wake-up control (EL-167).
- Risk: low. Init bytes only start a session. Still, never scan with the car in gear or moving.

### Phase 2: Identify + self-diag (read-only)

For each found unit:

- [ ] `D0 F0` → log the frame, then decode it like the engine part number
      (`XXXX 23710-YYYYY`) with the prefix changed.
- [ ] `D1 F0` → log. Compare with the manual's self-diag lists.
  - **Create known faults on purpose**, for example unplug a door's LCU connector for
    > 1 minute ("disconnected data will be memorised by the BCM", EL-90). Then read `D1`
    and see which code byte appears. Expect it to match the blink codes 24/25/34/…
    The encoding question (`0x24` vs `24` decimal) is the same as for engine DTCs.
  - Then **erase** with `C1 F0`, re-read, and confirm it cleared. Cross-check with
    on-board Mode I blink codes.
- [ ] Try `9F F0` (stream all). If it works, one frame contains every data-monitor
      value, which makes Phase 3 much easier.

### Phase 3: Map data-monitor registers (read-only)

1. **Support scan:** for `r` in `00..FF`, send `5A r F0`. Record whether the echo is
   `A5 r` and the first frame value. Then send `30`. This gives the list of live
   registers on the unit.
2. **Differential logging:** stream all supported registers (in batches of ≤ 20) while
   doing **one action at a time**, with a note saying what you did:
   - Key in / out → `IGN KEY SW`
   - ACC / ON → `IGN ACC SW` / `IGN ON SW`
   - Each door open/closed, hood, trunk → door/hood/trunk switches
   - Seat belt, headlamp 1st position, wiper INT, washer, defogger switch
   - Rotate the intermittent knob slowly → the register that changes smoothly is
     `INT RESIST`. Record raw values at both ends to fit the kΩ scale (0 → ≈ 1.0).
   - Each power-window switch, the lock switch, the key cylinder lock/unlock, remote
     buttons (lock, unlock, panic, trunk)
   - Drive slowly with a passenger running the tool → `VHCL SPEED SE` scale (compare
     with GPS)
   - A script then flags which **byte** and **bit** changed for each action. That
     gives `{register, bit} → item name`.
3. **Cross-check** every mapped switch against BCM on-board **Mode II** (lamp + buzzer
   on each detected switch).
4. **ASCD**: the same method. Brake pedal, set/resume/cancel, then a road test with a
   passenger for `SET VHCL SPD`, `VACUUM PUMP` / `AIR VALVE` msec values and
   fail-safe flags.
5. **AIRBAG**: **read-only**: `D0`, `D1` and the register scan only. See safety below.

### Phase 4: Ground truth from a real tool (strongly recommended)

The Phase 3 method finds *where* data lives. It cannot reveal special commands
(IVMS COMM DIAGNOSIS, WAKE-UP DIAGNOSIS, active-test encodings). The fastest way to get
those is to watch a tool that already knows them:

- **Genuine Nissan CONSULT-I hand-held** (with the right program card): build a passive
  tap that sits between it and the car's connector, putting the TX and RX lines into
  two USB-serial RX pins at 9600 8N1. Log while going through every IVMS / ASCD /
  AIRBAG menu. This is the gold standard. Used units sometimes come up for sale, and
  some Nissan specialists still have them.
- **Any Windows tool that lists IVMS/BCM** (check whether ECUTalk does): run it in a
  VM and capture USB traffic with `usbmon` + Wireshark on the Linux host, as described
  in `CONSULT_PROTOCOL.md` §13.
- Ask the Nissan Technical egroup successors (nistune forum, maxima.org, ecutalk
  forums) whether anyone has logs. Others with IVMS cars (I30/Maxima) may have done this.

### Phase 5: ROM dump & disassembly (optional, high payoff)

- [ ] Try `C9` reads on the BCM/ASCD (`C9 80 00 F0`). If the echo is `36 80 00` and a
      frame comes back, dump `0x8000–0xFFFF`.
- [ ] Identify the CPU. Open the unit and read the chip markings.
- [ ] Find the Consult command dispatcher in the disassembly. It will be a table or
      switch on the bytes `5A`, `D0`, `D1`, `C1`, `0A`… plus any **unknown bytes**.
      Those unknown bytes are the IVMS COMM / WAKE-UP / erase commands. The `0A`
      handler shows the active-test register numbers and value ranges.
- Risk: reads are harmless. **Never** experiment with write-type commands found in the
  ROM.

### Phase 6: Active tests (outputs). Careful, incremental

Order from most to least benign. Test one at a time, with doors open and windows
partly down (so you can't lock yourself out), and a hand ready to pull the fuse:

1. `ILLUM LAMP`, `ROOM LAMP TIMER`, `STEP LAMP`, security `INDICATOR LAMP`
2. Buzzers: `IGN KEY WARN ALM`, `LIGHT WARN ALM`, `SEAT BELT WARN ALM`
3. `HAZARD`, `RR DEFOGGER RLY`, `WIPER AMP` (wet the windshield first)
4. Door lock motors (keys **outside** the car is a bad idea; keep a door open)
5. Power windows (keep hands and objects clear; watch for pinching)
6. `ALARM RELAY` (horn/lights; warn the neighbours), `INTERRUPT RELAY` (starter cut;
   engine OFF only)

Method: if Phase 4/5 did not already reveal the encoding, try `0A <t> <v> F0` with
`t` in the `80–9F` range (the engine uses that range) and `v = 00`/`01`. Watch for the
inverted echo `F5 t v` and a physical effect. **Always** send `30` afterwards and
confirm the output returns to normal.

### Phase 7: Special IVMS functions

- **IVMS COMM DIAGNOSIS / WAKE-UP DIAGNOSIS / ERASE** are described as procedures the
  BCM runs on request. Implement them once their command bytes come from Phase 4 or 5.
- Until then, the tool can show the **equivalent result** from `D1` and erase it with
  `C1` (if Phase 2 confirms that works), and walk the user through **on-board Mode I**
  as a fallback.

---

## 4. Safety rules (put these in the tool too)

- **AIRBAG (SRS): read-only, forever.** No active tests, no ROM experimenting, no
  unknown commands. A mistake could deploy an airbag or disable it. Leave the SRS
  connectors alone (yellow harness).
- No active tests with the vehicle moving. The tool should refuse them unless
  `VHCL SPEED SE == 0` and `IGN` state is sane.
- Always end every operation with `30` and a drain. On exit or crash, try
  to restore outputs.
- Keep a battery charger on during long ignition-ON sessions.
- **Don't run unknown bytes against the ENGINE ECU.** Do discovery work on the body
  units only.

---

## 5. Deliverables / definition of done

| Milestone | Output |
|---|---|
| M1 | `probe scan-init` finds every unit. A table of init byte → unit + part number |
| M2 | `D1`/`C1` working for BCM & ASCD, with code → manual text tables |
| M3 | `profiles/ivms_bcm.yaml` + `profiles/ascd.yaml` with ≥ 90 % of the §1.4/§1.5 data-monitor items mapped and verified against Mode II |
| M4 | Active tests for lamps, buzzers, hazard, defogger, wiper, locks, windows |
| M5 | IVMS COMM / WAKE-UP diagnosis and erase memory (needs Phase 4 or 5) |
| M6 | A write-up appended to `CONSULT_PROTOCOL.md` (a new §, "Body units") so others can reuse it |

## 6. Open questions to answer along the way

1. Is the init reply always `~address`?
2. Do body units use the same `5A`/`D1`/`C1`/`0A` command set as the engine, or
   unit-specific bytes like the A/T unit's `9F` / `F0` "ECU info"?
3. Is the BCM reachable while "asleep", or does Consult wake it?
4. Does ECUTalk support any of these units? If it does, capturing it shortens
   Phases 3–7 a lot.
5. Does the BCM report LCU states (window motor, unlock sensors) as its own registers,
   or through separate sub-addresses?
