# On-Car Test Checklist

This is everything to check once the scanner is connected to the 1998 Maxima. It
gathers the open questions from `CONSULT_PROTOCOL.md` (§12) and `BODY_DIAG_PLAN.md`.

**Log every session raw**: every TX/RX byte, timestamped. Save the logs in `logs/`,
named `YYYY-MM-DD_<test-id>.log`. A test is done when the result is written in its
"Result" line **and** the log file is saved.

Legend for conditions:
- **KOEO**: key on, engine off
- **KOER**: key on, engine running (warm idle unless noted)
- **Charger**: battery charger connected (use it for long KOEO sessions)

---

## 0. Before connecting

- [ ] **0.1 Dongle on Linux.** Plug the dongle into the PC only (not the car yet). Run
      `lsusb`, `dmesg | tail` and `ls /dev/ttyUSB*`.
      Record: VID:PID, chip type, driver, device node.
      Result: ____
- [ ] **0.2 Custom PID?** If no `/dev/ttyUSB*` appears, bind it with
      `echo 0403 <pid> > /sys/bus/usb-serial/drivers/ftdi_sio/new_id`.
      Result: ____
- [ ] **0.3 Permissions.** Your user can open the port without sudo (`uucp`/`dialout` group).
      Result: ____
- [ ] **0.4 Latency timer.** Read `/sys/bus/usb-serial/devices/ttyUSB0/latency_timer`
      (the default is probably 16), then set it to 1.
      Result: ____
- [ ] **0.5 Locate connectors.** Find the 14-pin Consult connector (grey, near the fuse
      block) and the 16-pin OBD-II connector. Take photos.
      Result: ____
- [ ] **0.6 Confirm the manual.** Check the `EL.pdf` cover: is it the 1998 Maxima?
      Result: ____
- [ ] **0.7 ECU label.** Read the part number on the ECU sticker (`23710-xxxxx`). It is
      checked against the `D0` result in 2.1.
      Result: ____

## 1. Link basics (engine ECU, KOEO)

- [ ] **1.1 Init.** Send `FF FF EF`. Expect `10`. Record how many attempts it took and
      how long the reply took.
      Result: ____
- [ ] **1.2 Init twice in a row.** What does the ECU send back to a second init while
      it's already initialised?
      Result: ____
- [ ] **1.3 Init without the 2 s wait.** Does it work immediately?
      Result: ____
- [ ] **1.4 Init while streaming.** Start a stream, then send the init again. Does the
      ECU recover, or does it need `30` first?
      Result: ____
- [ ] **1.5 Stop acknowledge.** Stream one register, send `30`, and log every byte
      after it. **Is the ack `CF` or `FE`?** How many bytes of the current frame arrive
      before the ack?
      Result: ____
- [ ] **1.6 Bad echo behaviour.** Send an invalid command byte (e.g. `5B`). What comes
      back: nothing, a non-inverted echo, or garbage?
      Result: ____
- [ ] **1.7 Idle timeout.** Initialise, then wait 5, 15 and 30 minutes, then send a
      command. Is a re-init needed?
      Result: ____
- [ ] **1.8 Key cycle.** Turn the key off, then back on. Is a re-init needed? (It
      probably is.)
      Result: ____

## 2. ECU ID and fault codes (engine)

- [ ] **2.1 `D0` part number.** Log all 22 raw bytes. Does the openconsult decoding
      (`d[2] d[3] … d[19] d[20] d[21]`) match the sticker from 0.7?
      Result: ____
- [ ] **2.2 `D0` other bytes.** Do the 17 unexplained bytes look like ASCII,
      calibration IDs, or something else?
      Result: ____
- [ ] **2.3 `D1` with no faults.** **Is the "no fault" code byte `0x55` or `0x37`?**
      This settles the hex-vs-decimal question for codes.
      Result: ____
- [ ] **2.4 `D1` with a known fault.** KOEO: unplug the coolant temp sensor (or the
      IAT sensor). Key off, key on. Read `D1`. Record the code byte.
      Expected: a code for coolant (13 or 0x13?) or the 1996+ 4-digit equivalent.
      Compare with a generic OBD-II scan of the same fault.
      Result: ____
- [ ] **2.5 Starts counter.** Keep the fault from 2.4 stored, fix the cause, and do a
      few start cycles. Does the second byte count the starts?
      Result: ____
- [ ] **2.6 `C1` clear.** Clear the codes, re-read `D1` and confirm they're gone. Also
      check with a generic OBD-II scanner.
      Result: ____
- [ ] **2.7 Number of DTC pairs.** With 2 or more faults stored, is the frame length
      2 × the number of faults?
      Result: ____

## 3. Live data registers (engine)

- [ ] **3.1 Register support scan.** For each register `00..FF`: send `5A r F0`, record
      the echo and the first value, then send `30`. Make a list of supported registers
      for the VQ30DE.
      Result: ____
- [ ] **3.2 What an unsupported register does.** Record the exact reply: no echo, a
      wrong echo, or a frame of `00`?
      Result: ____
- [ ] **3.3 20-register limit.** Request 20 registers, then 21. What happens at 21?
      Result: ____
- [ ] **3.4 Frame rate.** Measure frames per second for 1, 4, 10 and 20 registers, with
      the latency timer at 16 and at 1.
      Result: ____
- [ ] **3.5 RPM.** Compare `00/01` × 12.5 with the tach at idle and at about 2500 rpm.
      Result: ____
- [ ] **3.6 CAS reference.** Is `02/03` × 8 also equal to RPM?
      Result: ____
- [ ] **3.7 Coolant / IAT.** Compare `08` and `11` (value − 50) with an IR thermometer
      or the gauge, cold and warm.
      Result: ____
- [ ] **3.8 Battery voltage.** Compare `0C` × 80 mV with a multimeter on the battery,
      KOEO and KOER.
      Result: ____
- [ ] **3.9 TPS.** `0D` × 20 mV at closed and at wide-open throttle (KOEO). Compare
      with the FSM spec.
      Result: ____
- [ ] **3.10 MAF.** `04/05` × 5 mV at idle. Compare with the FSM spec (about 1.0–1.7 V
      at idle, typically).
      Result: ____
- [ ] **3.11 O2 sensors.** `09` and `0A` should switch between 0 and about 900 mV at
      2000 rpm. **Which register is bank 1 and which is bank 2 on the VQ?**
      Result: ____
- [ ] **3.12 Vehicle speed.** Drive with a passenger running the tool. Compare `0B` × 2
      with GPS at 30 / 60 / 100 km/h. Is ×2 right, or is it closer to Nissboard's ×2.11?
      Result: ____
- [ ] **3.13 Injection time.** `14/15` / 100 ms at idle (expect about 2–3 ms). Is
      `22/23` present on this engine?
      Result: ____
- [ ] **3.14 Ignition timing.** `16` → 110 − v. Compare with a timing light at idle
      (the FSM base timing is about 15° BTDC, so verify).
      Result: ____
- [ ] **3.15 AAC.** `17` / 2 %. Watch it rise when the A/C or a heavy electrical load
      is switched on.
      Result: ____
- [ ] **3.16 A/F alpha.** `1A`–`1D`: around 100 % at closed-loop idle? Do the
      self-learn registers respond?
      Result: ____
- [ ] **3.17 Bit register `13`.** Toggle each of these and record the bit that changes:
      A/C switch, power steering (turn the wheel at idle), P/N (shift), start signal
      (crank), closed throttle.
      Result: ____
- [ ] **3.18 Bit register `1E`.** A/C relay, fuel pump relay (it primes at KOEO), VTC
      solenoid (if fitted), coolant fan Lo/Hi.
      Result: ____
- [ ] **3.19 Bit register `1F`.** Pressure regulator valve, IACV-FICD, EGR.
      Result: ____
- [ ] **3.20 Register `21`.** Do the rich/lean bits follow the O2 sensors?
      Result: ____
- [ ] **3.21 Unscaled registers.** For each of `25`–`53` that is supported: log the raw
      values alongside a reference (a multimeter on the sensor, etc.) and fit a scale.
      Result: ____

## 4. Active tests (engine). KOER, parked, warm, handbrake on

Do them one at a time. Restore the normal value and send `30` after each.

- [ ] **4.1 `0A 81` fuel trim.** Send `64` (normal), then `6A` (+6 %), then `5E`
      (−6 %). Do injection time and O2 readings shift the expected way?
      Result: ____
- [ ] **4.2 `0A 82` timing.** `00`, `02` (+2°), `FE` (−2°). Check with a timing light
      and register `16`.
      Result: ____
- [ ] **4.3 `0A 84` AAC.** **Is the value signed ±0.5 % steps or absolute 0–`8C`?**
      Start with `00` and watch register `17`, then try `02`.
      Result: ____
- [ ] **4.4 `0A 88` power balance.** **Is the value a bitmask (`01`, `02`, `04`…) or a
      cylinder number (`01`–`06`)?** Watch the RPM drop. Record which cylinder number
      matches which bit.
      Result: ____
- [ ] **4.5 `0A 89` fuel pump.** Do this KOEO only. **Does `00` mean ON or OFF?**
      Listen for the pump.
      Result: ____
- [ ] **4.6 `0A 80` coolant override.** Set it to 100 °C (`96`). Does the cooling fan
      turn on? Send `30` and confirm it returns to normal.
      Result: ____
- [ ] **4.7 `0A 93` / `0A 94` fan Lo/Hi.** Do the fans run?
      Result: ____
- [ ] **4.8 `0A 8B` clear self-learn.** Does register `1C` reset? (Do this last. It
      resets the fuel trims, and the car re-learns them.)
      Result: ____
- [ ] **4.9 Active test echo format.** Is the echo `F5 t v`?
      Result: ____

## 5. ROM / RAM read (engine)

- [ ] **5.1 Single byte.** `C9 80 00 F0`. Expect the echo `36 80 00` and a frame
      `FF 01 xx`.
      Result: ____
- [ ] **5.2 8-byte limit.** Read 8 addresses, then 9. What happens at 9?
      Result: ____
- [ ] **5.3 Full dump.** Read `0x8000–0xFFFF` and save it to `rom/<partnumber>.bin`.
      Time how long it takes.
      Result: ____
- [ ] **5.4 Repeatability.** Dump it a second time. Is the result byte-identical?
      Result: ____
- [ ] **5.5 Below 0x8000.** Read a few addresses in `0x0000–0x7FFF` (RAM and I/O). Do
      some values change between reads at idle? If so, those are live variables.
      Result: ____
- [ ] **5.6 Compare with ECUTalk.** If possible, dump with ECUTalk too and compare the
      two files.
      Result: ____

## 6. Other control units (KOEO, Charger)

- [ ] **6.1 A/T unit.** Send `FF FF EA`. **Is the reply `15` (= ~EA)?** This tests the
      complement hypothesis.
      Result: ____
- [ ] **6.2 Init scan.** Try `FF FF xx` for every `xx` from `00` to `FF`, sending `30`
      and draining between tries. List every value that gets a reply.
      Result: ____
- [ ] **6.3 Repeat 6.2 KOER and with the ASCD main switch ON.** Do any new units appear?
      Result: ____
- [ ] **6.4 Identify each hit.** Run `D0` on each, and pull fuses one at a time to see
      which unit drops out. Write down which init byte is the BCM, the ASCD and the
      airbag unit.
      Result: ____
- [ ] **6.5 A/T data.** Run `9F` (stream all). Record the frame layout. Check gear,
      selector position and fluid temperature against reality.
      Result: ____

## 7. IVMS / BCM (see BODY_DIAG_PLAN.md)

- [ ] **7.1 BCM `D0` / `D1`.** Record the raw frames.
      Result: ____
- [ ] **7.2 Create a known fault.** Unplug one door's LCU for more than 1 minute, plug
      it back in, and read `D1`. Record the code byte. Is it 24/25, 34/35, etc.? Compare
      with the on-board Mode I blink code.
      Result: ____
- [ ] **7.3 Erase.** Does `C1` clear it?
      Result: ____
- [ ] **7.4 Stream all.** Does `9F` work on the BCM?
      Result: ____
- [ ] **7.5 Register scan.** Send `5A 00..FF` to the BCM and list the supported registers.
      Result: ____
- [ ] **7.6 Differential logging.** Change one input at a time and record which byte
      and bit changes:
  - [ ] Key in / out
  - [ ] ACC
  - [ ] ON
  - [ ] Each door: DR, AS, RR, RL
  - [ ] Hood
  - [ ] Trunk
  - [ ] Trunk key cylinder
  - [ ] Seat belt
  - [ ] Headlamp 1st position
  - [ ] Wiper INT
  - [ ] Washer
  - [ ] Defogger switch
  - [ ] Each power-window switch (up / down / auto)
  - [ ] Window lock switch
  - [ ] Door lock switch (lock / unlock)
  - [ ] Key cylinder lock / unlock, DR and AS
  - [ ] Each door's unlock sensor
  - [ ] Remote fob: lock, unlock, panic, trunk
      Result: ____
- [ ] **7.7 Intermittent wiper knob.** Sweep the knob from end to end. Which register
      changes smoothly? Record the raw values at each end so the kΩ scale (0 to about
      1.0) can be fitted.
      Result: ____
- [ ] **7.8 BCM speed.** Drive and compare the BCM's `VHCL SPEED SE` with engine
      register `0B`.
      Result: ____
- [ ] **7.9 Mode II cross-check.** Put the BCM into on-board Mode II (EL-178). Check
      that every switch mapped in 7.6 also triggers a lamp blink and beep.
      Result: ____
- [ ] **7.10 Side effects.** While connected, does the intermittent wiper stop working
      (as EL-101 says)? Note any other systems that stop.
      Result: ____
- [ ] **7.11 Sleep.** Key off, doors closed, wait for the BCM to go to sleep. Does it
      answer init? Does Consult wake it up?
      Result: ____

## 8. BCM active tests (only after section 7; doors open, windows partly down)

- [ ] **8.1 `C9` on the BCM.** Can the BCM's ROM be read? If yes, dump it first
      (this is safer than guessing active-test codes).
      Result: ____
- [ ] **8.2 Lamps.** Illumination, room lamp, step lamp, security indicator.
      Result: ____
- [ ] **8.3 Buzzers.** Key warning, light warning, seat-belt warning.
      Result: ____
- [ ] **8.4 Hazard, rear defogger relay, wiper amp.** Wet the windshield before
      running the wiper.
      Result: ____
- [ ] **8.5 Door lock motors.** One door at a time. Keep the key in your pocket, not
      in the car, and keep a door open.
      Result: ____
- [ ] **8.6 Power windows.** Keep hands and objects clear.
      Result: ____
- [ ] **8.7 Alarm relay, starter interrupt relay.** Engine OFF.
      Result: ____

## 9. ASCD cruise control (ASCD main switch ON)

- [ ] **9.1 Find it.** Find the ASCD unit's init byte (see 6.3), then run `D0` and `D1`.
      Result: ____
- [ ] **9.2 Register scan.** Map the inputs: brake switch, stop lamp switch, SET,
      RESUME/ACC, CANCEL.
      Result: ____
- [ ] **9.3 Road test with a passenger.** Map vehicle speed, set speed, vacuum pump
      time, air valve time, cruise lamp, OD cancel and the fail-safe flags.
      Result: ____

## 10. Airbag / SRS (READ ONLY)

- [ ] **10.1 Find it.** Find its init byte (from 6.2), then run `D0` and `D1` only.
      **No `0A`, no unknown commands, no unplugging SRS connectors.**
      Result: ____

## 11. Hardware (key off, battery disconnected)

- [ ] **11.1 Remove the ECU.** Photograph both sides of the circuit board.
      Result: ____
- [ ] **11.2 ROM type.** **Is there a socketed 28-pin EPROM, or a single big CPU with
      the ROM inside it?** This decides which tuning route is possible.
      Result: ____
- [ ] **11.3 Chip markings.** Record the part numbers of the CPU, ROM, RAM, and
      whatever chip handles the Consult interface.
      Result: ____
- [ ] **11.4 Consult pins.** Trace the TX, RX and CLK pins from the ECU connector into
      the board.
      Result: ____

## 12. ECUTalk capture (optional, high value)

- [ ] **12.1 Body units?** Do ECUTalk's menus offer IVMS / BCM / ASCD / airbag?
      Result: ____
- [ ] **12.2 Capture.** Run ECUTalk in a Windows VM, capture with `usbmon` + Wireshark,
      and go through every menu.
      Result: ____
- [ ] **12.3 Capture its ROM dump.** Record ECUTalk's ROM dump sequence. Is it the
      same as `C9` in 8-byte chunks?
      Result: ____
- [ ] **12.4 Unknown bytes.** Note any command bytes ECUTalk sends that aren't in
      `CONSULT_PROTOCOL.md` §5.
      Result: ____
