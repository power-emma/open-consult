# Nissan Consult-I protocol reference

The Consult-I (DDL1) byte protocol, as published and as a 1998 Maxima (A32, VQ30DE,
ECU 23710-2L904) actually behaves. Source tags `[S1]`… are listed at the end. **A32**
marks behaviour observed on that car.

## 1. Physical layer

| Signal | Direction | Notes |
|---|---|---|
| RX (into unit) | host → unit | 12 V logic, idle low `[S1]` |
| TX (out of unit) | unit → host | Open collector, pulled up by the interface, idle high `[S1]` |
| CLK | host → unit | 153.6 kHz (16 × 9600), free-running. **No reply without it.** USB cables generate it `[S1]` |
| Serial | | 9600 8N1, raw binary, no checksums `[S1]` |

**A32 connector** (grey 14-pin, FSM EL-180 / BR-33 / RS-31): pin 1 = unit RX, pin 2 =
unit TX, pin 7 = cable power (**IGN-fed**, so nothing answers at ACC). The ECM uses
pins 75/76/78 (TX/RX/CLK); the BCM, ABS and airbag units have no clock line.

## 2. Linux setup

| Step | Command / setting |
|---|---|
| Driver | FTDI `0403:6001` binds to `ftdi_sio` → `/dev/ttyUSB0`. Custom PID: `echo 0403 <pid> > /sys/bus/usb-serial/drivers/ftdi_sio/new_id` `[S9][S10]` |
| Permissions | Group `dialout` (Debian) / `uucp` (Arch), or a udev rule with `MODE="0666"` |
| Latency | `echo 1 > /sys/bus/usb-serial/devices/ttyUSB0/latency_timer` (default 16 ms) |
| termios | 9600, `CS8`, no parity, 1 stop, no flow control, raw. **Use a read timeout** |
| Modem lines | **A32:** drop DTR and RTS after opening |

## 3. Session

```
host: FF FF <id>             unit: ~id           (init)
host: <cmd> [args]           unit: ~cmd [args]   (echo: command inverted, args verbatim)
host: F0                     unit: FF n d1..dn   (frames repeat until stopped)
host: 30                     unit: CF            (after the current frame)
```

Rules:
1. **Init:** `FF FF <id>`; the reply is `~id` `[S1]`. **A32 engine: `ED` → `12`**
   (not `EF` → `10`), preceded by `00 00`. ECUTalk's timing works: `FF`, 280 ms, `FF`,
   70 ms, ID.
2. **A wrong ID locks the A32 ECU** until a correct init: after `FF FF EF` it ignores
   everything, even `30`.
3. Stop and drain (`30`, read until `CF` or silence) before any new command or init.
4. Check every echo. An unsupported command or argument comes back as `FE`.
5. Send `F0` once. Frames stream until `30`, even for one-shot commands `[S1]`.
6. Parse frames by the length byte. Data bytes can be `FF`.
7. **Stop ack is `CF` or `FE`** (A32: ~94 % / ~6 %). Accept both, with a timeout.
8. **A32 echo glitches** (retry fixes both): `FE FE` instead of the first echo pair;
   `FE` in reply to `F0` with no frames (mostly single-register requests).
9. **Non-engine units** (A32 BCM): send one byte at a time, each after its echo. See
   [`BCM.md`](BCM.md).

## 4. Commands

| Cmd | Echo | Args | Reply | A32 engine |
|---|---|---|---|---|
| `FF FF <id>` | `~id` | | | `ED` → `12` |
| `5A` | `A5` | register | 1 byte per register, in request order | Registers `00–61` only; up to 40 per request (ROM) |
| `D0` | `2F` | | Part number | 32 bytes, ends ASCII `2L904` |
| `D1` | `2E` | | (code, starts) pairs | §8 |
| `C1` | `3E` | | Codes as they were, then cleared | ✓ |
| `C9` | `36` | addr hi, lo | 1 byte per address | Up to 20 per request (ROM); `5D40–623F` forwarded to the 2nd CPU |
| `0A` | `F5` | test, value | `FF 00` while held | Tests `80–AD` (§7) |
| `51` | `AE` | | Clears "seen this cycle" flags | Undocumented; don't send |
| `9F` | `60` | | Stream all (A/T, HICAS units) `[S3]` | Not supported |
| `30` | `CF` | | Stop | |

Generic limits from `[S1]`: 20 registers per `5A` request, 8 addresses per `C9`.

## 5. Engine registers (`5A`)

`word = MSB << 8 | LSB`. Generic formulas from `[S3]`/`[S2]`; A32 column from the car
and the ROM (`ROM_ANALYSIS.md` §2). ✓ = confirmed on the car. ✗ = not supported.

| Reg | Name | Formula | A32 |
|---|---|---|---|
| `00/01` | RPM | word × 12.5 | ✓ |
| `02/03` | CAS reference | word × 8 | ✗ formula: **rpm = 2 500 000 / word** (REF period) ✓ |
| `04/05` | MAF | word × 5 mV | ✓ |
| `06/07` | RH MAF | word × 5 mV | ✗ |
| `08` | Coolant | v − 50 °C | ✓ (streams only with other registers) |
| `09` / `0A` | O2 LH / RH | v × 10 mV | ✓ |
| `0B` | Speed | v × 2 km/h | ✓ (× 2.11 is wrong); updates every 0.707 s |
| `0C` | Battery | v × 80 mV | ✓ |
| `0D` | TPS | v × 20 mV | ✓ |
| `0F` | Fuel temp | v − 50 °C | ✗ |
| `10` | EGT sensor (A32) | v × 20 mV `[S12]` | supported |
| `11` | Intake air temp | v − 50 °C | ✓ |
| `12` | EGT sensor | v × 20 mV | ✗ |
| `13` | Switch bits | §6 | ✓ |
| `14/15` | Injection LH | word / 100 ms | ✓ |
| `16` | Timing | 110 − v ° BTDC | ✓ |
| `17` | AAC valve | v / 2 % | ✗ (use `18`) |
| `18` | IACV-AAC step (A32) | steps | supported |
| `1A` / `1B` | Alpha LH / RH | v % | ✓ |
| `1C` / `1D` | Self-learn LH / RH | v % | ✓ |
| `1E` / `1F` | Output bits | §6 | ✓ |
| `21` | O2 monitor bits | §6 | ✓ |
| `22/23` | Injection RH | word / 100 ms | ✓ |
| `29` | Purge volume control valve step (A32) | steps | supported *(inferred)* |
| `33/34` | CAL/LD (A32) | `33` + `34`/256 % `[S12]` | supported |
| `35` | Rear O2 | v × 10 mV `[S12]` | supported |
| `37` | Absolute throttle | v / 2.55 % `[S12]` | supported |
| `38` | MAF (% of VQ table) | × 272 / 100 g/s `[S12]` | supported |
| `3B–47`, `51` | Freeze frame (A32) | | supported |
| `4A` | Absolute pressure sensor | v × 20 mV `[S12]` | supported |
| `56–5F` | 1st-trip freeze frame (A32) | | supported |

Other generic registers (`25–2F`, `30–32`, `36`, `39`, `3A`, `52/53`) have no published
scaling. **A32 supported set (73):** `00–05 08–0D 10 11 13–16 18 1A–23 28–2A 30–35
37–3F 40–47 49 4A 4C 4E 4F 51 56–61`.

## 6. Bit registers

Generic `[S3]` (1 = active):

| Reg | b7 | b6 | b5 | b4 | b3 | b2 | b1 | b0 |
|---|---|---|---|---|---|---|---|---|
| `13` | | | | A/C sw | PS sw | P/N sw | Start | Closed throttle |
| `1E` | A/C relay | Fuel pump | VTC | | | | Fan HI | Fan LO |
| `1F` | | P/Reg valve | Wastegate | | FICD | | | EGR |
| `21` | LH lean | RH lean | | | | | | |

A32, from the car:

| Reg | Bits |
|---|---|
| `13` | b4 A/C switch, b3 power steering, b2 neutral (1 = N), b0 closed throttle, b5 rear-defrost load, b7 always 1 |
| `1E` | b6 fuel pump relay *(inferred)*; b1 and b7 with A/C |
| `1F` | b0 briefly on a throttle blip |
| `21` | b7 = `09` lean, b6 = `0A` lean (< ~450 mV); b0 latches on after warm-up; b5/b4 always 1 |

## 7. Engine active tests (`0A <test> <value> F0`)

**Safety:** these change fuel, timing, idle air, pumps and fans. Parked, engine warm.
Restore the normal value, then `30`. **On a 1999 A32 ECU an unknown test above `9F`
(believed `B0`) re-registered the immobiliser keys `[S12]`. Never fire unknown IDs.**

| Test | Name | Values (generic) | A32 |
|---|---|---|---|
| `80` | Coolant override | temp + 50 | supported |
| `81` | Fuel trim | `64` = 100 %, ±1 %/step | clamped `4B–7D` (75–125 %) |
| `82` | Timing offset | signed degrees | supported |
| `84` | IACV-AAC opening | ⚠ sources disagree | ✗ |
| `85` | IACV opening | `00–8C` | supported (step, ≤ `81`) |
| `88` | Power balance | bitmask or cylinder no. | `01` cuts cylinder 1 ✓ |
| `89` | Fuel pump relay | ⚠ polarity disputed | supported |
| `8B` | Clear self-learn | `00` | supported |
| `93` / `94` | Fan LO / HI | `00` off | ✓; set as a pair: LO = `93 01` + `94 00`, HI = `93 00` + `94 01` `[S12]` |
| `98` | Purge volume control valve | | supported *(inferred)* |

A32 descriptors exist for `80 81 82 85 88 89 8B 8C 93 94 95 98 99 9A 9C A2 A6 A7 AA AB
AC AD`; everything else in `80–AD` and everything above `AD` gets `FE`. From `[S12]`
(1999 ECU): `9A`/`AB` canister vent valve, `9C`/`A7` vacuum cut bypass valve.

## 8. Fault codes

**A32:** the `D1` code byte is an index into a ROM table, not a Nissan code number;
`ROM_ANALYSIS.md` §3 maps each to its P-code. No faults = `55 00`. A starts byte of
`F5` = 1st-trip (pending) code.

Generic 2-digit codes (pre-1996 ECUs) `[S2]`:

| Code | Meaning | Code | Meaning |
|---|---|---|---|
| 11 | Crank angle sensor | 41 | Intake air temp sensor |
| 12 | MAF sensor | 42 | Fuel temp sensor |
| 13 | Coolant temp sensor | 43 | Throttle position sensor |
| 14 | Vehicle speed sensor | 45 | Injector leak |
| 21 | Ignition signal | 51 | Injector circuit |
| 22 | Fuel pump | 53 | O2 sensor |
| 23 | Idle switch | 54 | A/T communication |
| 25 | Idle speed control valve | **55** | **No malfunction** |
| 28 | Overheat | 63–68 | Cylinder 6…1 misfire |
| 31 | ECM | 71 | Random misfire |
| 32 | EGR function | 72 | TWC function RH |
| 33 | Heated O2 sensor | 76 | Fuel injection system RH |
| 34 | Knock sensor | 77 | Rear heated O2 sensor |
| 35 | EGT sensor | 98 | Coolant temp sensor |
| 37 | Knock sensor | 103 | Park/neutral switch |

## 9. Other units

| Init | Unit | Notes |
|---|---|---|
| `EF` | Engine (generic) `[S3]` | |
| `EA` | A/T `[S3]` | `9F` stream all |
| `E4` | S-HICAS `[S3]` | |
| `DF` | Auto A/C `[S3]` | |
| **A32:** `ED` → `12` | Engine ECM 23710-2L904 | |
| **A32:** `DA` → `25` | BCM (IVMS) 28491-2L900 | Paced; see [`BCM.md`](BCM.md) |
| **A32:** `DC` → `23` | Airbag unit | Consult switches it to diagnosis mode (lamp flashes). **Read-only** |
| **A32:** `E7` → `18` | ABS 47850-0L701 | Only `D0` works. **Never `0A`** (drives brake solenoids) |

A/T registers `[S3]`: `00` VSS km/h, `01` meter speed km/h, `02` TPS v/50 V, `03` fluid
temp v/50 V, `04` battery v × 8/100 V, `06` rpm v × 32, `08–0A` bits, `0C` gear v + 1,
`0D` selector (`83` P/N, `82` 1, `81` 2, `80` D, `87` R), `0E` speed, `0F` throttle
v/2.55 %, `10` line pressure duty, `11` TCC duty.

## 10. Implementation rules

1. Stop and drain before every command.
2. Parse by length, never by scanning for `FF`.
3. Time out every read.
4. Confirm a register by streaming it with others; single-register requests are
   unreliable on the A32.
5. Python 3: write `bytes([0x30])`, not `0x30` `[S4]`.

## Sources

- **[S1]** Nissan Technical egroup, *Consult Protocol & Commands*, Issue 5/6 (2003):
  [Issue 6](https://www.plmsdevelopments.com/images_ms/Consult_Protocol_&_Commands_Issue_6.pdf)
- **[S2]** jonsim, *openconsult*: <https://github.com/jonsim/openconsult>
- **[S3]** PLMS, *Generic Nissan Engine ECU Register Table* v2:
  [PDF](https://www.plmsdevelopments.com/images_ms/Generic_Nissan_ECU_Sensor_or_Data_register_table_Ver_2.pdf)
- **[S4]** fridlington, *K11Consult* <https://github.com/fridlington/K11Consult>;
  matiasmenares, *Nissboard* <https://github.com/matiasmenares/Nissboard>
- **[S9]** FTDI TN_101 (custom VID/PID on Linux)
- **[S10]** Nistune forum, *PLMS USB Cable Drivers for Linux?*: <https://nistune.com/forum/viewtopic.php?p=10431>
- **[S12]** PLMS, *1999 Nissan Maxima "A32, VQ30DE" Consult Data Registers* (2008):
  <https://www.plmsdevelopments.com/files/1999_a32_maxima_obd2_registers.pdf>
