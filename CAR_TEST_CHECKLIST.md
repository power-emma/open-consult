# On-car test checklist

Tests run on a 1998 Maxima (VQ30DE, 5-speed, ECU 23710-2L904).

- **Logs:** `logs/maxine-2026-11-14_<name>.log`; the Log column gives `<name>`.
- **Conditions:** KOEO = key on, engine off. KOER = engine running, warm idle unless noted.
- **Status:** ✅ done · ◐ partial · ☐ open · — not applicable

## 0. Setup

| # | Test | | Result | Log |
|---|---|---|---|---|
| 0.1 | Dongle on Linux | ✅ | FTDI FT232R `0403:6001`, `ftdi_sio`, `/dev/ttyUSB0`. EEPROM factory default (CBUS = LED/TXDEN/PWREN/SLEEP), so the cable makes its own clock | `1.1` |
| 0.2 | Custom PID | ✅ | Not needed (stock PID) | |
| 0.3 | Permissions | ✅ | udev rule: `MODE="0666"`, symlink `/dev/consult` | |
| 0.4 | Latency timer | ✅ | Default 16 ms; the udev rule sets 1 ms | |
| 0.5 | Locate connectors | ☐ | | |
| 0.6 | Confirm the manual | ✅ | `fsm/` is the 1998 Maxima manual | |
| 0.7 | ECU label | ✅ | 23710-2L904, matches `D0` | |

## 1. Link (engine, KOEO)

| # | Test | | Result | Log |
|---|---|---|---|---|
| 1.1 | Init | ✅ | **ID `ED`, not `EF`:** `FF`, 280 ms, `FF`, 70 ms, `ED` → `00 00 12`, first try, 3–30 ms. `FF FF EF` → `00 00`, then the ECU ignores everything (even `30`) until a correct init. Drop DTR/RTS after opening the port | `1.1-linux`, `1.1-win-ED`, `1.1-win-variants` |
| 1.2 | Init twice in a row | ☐ | | |
| 1.3 | Init without byte gaps | ☐ | | |
| 1.4 | Init while streaming | ☐ | | |
| 1.5 | Stop ack | ✅ | `CF` (~94 %) or `FE` (~6 %). Only whole frames arrive before the ack | `1.5-win-py`, `3.1-win-py` |
| 1.6 | Invalid command byte | ✅ | `FE` | `3.1-win-py` |
| 1.7 | Idle timeout | ☐ | | |
| 1.8 | Key cycle | ☐ | | |

## 2. ID and fault codes (engine)

| # | Test | | Result | Log |
|---|---|---|---|---|
| 2.1 | `D0` | ✅ | Echo `2F`, **32 bytes**: `20 21 04 9D 00 00 00 3F C1 80 C3 00 10 7C 05 00 E5 07 00 01 00 00 00 00 00 FF FF 32 4C 39 30 34`; ends ASCII `2L904`. The openconsult decoding doesn't apply | `2.1-win-D0b` |
| 2.2 | `D0` other bytes | ☐ | Not a register or test bitmap (ROM) | |
| 2.3 | `D1` | ✅ | No faults = `55 00`. Code byte = slot index, decoded via ROM tables (`ROM_ANALYSIS.md` §3). Stored: `21` P1320, `34` P0325, `A8` P0443 | `2.3-win-py`, `dtc-after-clear` |
| 2.4 | `D1` with a known fault | ☐ | | |
| 2.5 | Starts counter | ☐ | | |
| 2.6 | `C1` clear | ✅ | Echo `3E`; the frame shows the codes *before* the clear; `D1` after = `55 00`. `21` and `A8` returned as `xx F5` (`F5` = 1st-trip / pending, MIL off) | `gui`, `dtc-after-restart` |
| 2.7 | Frame length vs code count | ◐ | 6 bytes for 3 codes | `2.3-win-py` |
| 2.8 | P1320 monitor live | ◐ | **Continuous:** detected 2–5×/s; P4.3 high 36 % (idle) to 92 % (high load). Next: `p1320` while unplugging one coil at a time (`ROM_ANALYSIS.md` §7) | `2.8-p1320-drive` |

## 3. Live data (engine)

| # | Test | | Result | Log |
|---|---|---|---|---|
| 3.1 | Register scan | ✅ | 73 supported: `00–05 08–0D 10 11 13–16 18 1A–23 28–2A 30–35 37–3F 40–47 49 4A 4C 4E 4F 51 56–61`. `17` not supported. `04 08 37 46` stream only alongside other registers | `3.1-win-py`, `3.1-koer-rescan` |
| 3.2 | Unsupported register | ✅ | Echo `A5 FE`. A valid one sometimes gets `FE FE` (retry fixes it) | `3.1-win-py` |
| 3.3 | 20-register limit | ☐ | ROM allows 40 | |
| 3.4 | Frame rate | ◐ | 19 regs ≈ 39 fps (latency 16); 21 regs ≈ 32.5 fps (latency 1) | `3.x-koer-idle`, `3.x-drive` |
| 3.5 | RPM `00/01` | ✅ | × 12.5 matches the tach | `3.x-koer-throttle2` |
| 3.6 | `02/03` | ✅ | 120° REF **period**: rpm = 2 500 000 / word (2.49 M at 1175 rpm, 2.50 M at 2500) | `3.x-koer-idle`, `3.x-drive` |
| 3.7 | Coolant `08` / IAT `11` | ◐ | Coolant − 50 matches the gauge. IAT unchecked | |
| 3.8 | Battery `0C` | ✅ | × 80 mV matches a meter | |
| 3.9 | TPS `0D` | ◐ | × 20 mV. KOER: closed 480 mV, WOT 4180–4200 mV. KOEO unchecked | `3.x-drive` |
| 3.10 | MAF `04/05` | ✅ | × 5 mV. Warm idle 1.09–1.34 V (spec 1.0–1.7), 2500 rpm 1.75 V, WOT 4.2 V | `3.x-koer-warm-idle`, `3.x-drive` |
| 3.11 | O2 `09` / `0A` | ◐ | × 10 mV, both switch 0–950 mV. Which bank is which: open | `3.x-koer-throttle2` |
| 3.12 | Speed `0B` | ✅ | **× 2** (not × 2.11): gear ratios give one rolling circumference, 1.985 m, in 3rd/4th/5th. Updates every 0.707 s | `3.x-drive` |
| 3.13 | Injection `14/15`, `22/23` | ✅ | / 100 ms, LH and RH bank. Warm idle 2.6 ms, WOT ~16 ms, fuel cut 0.61 ms | `3.x-drive` |
| 3.14 | Timing `16` | ◐ | 110 − v. Warm idle 5–15° (mostly 13°, moves against rpm). Part throttle 2000 rpm 39–41°. WOT 9–10° at 3750–4500 rpm, 15–16° above 5000, repeatable. Fuel cut reads 0. Timing light: open | `3.x-drive` |
| 3.15 | AAC `17` | — | Not supported; IACV step is `18` | |
| 3.16 | Alpha `1A–1D` | ◐ | `1A/1B` 102–107 % closed loop, 100 % open loop. `1C/1D` change with load cell (98–109 %). Fuel cut: ~1 s at 1.3 ms after lift-off, then 0.61 ms; fuel returns at 1460–1650 rpm | `3.x-drive` |
| 3.17 | Bits `13` | ◐ | b4 A/C, b3 power steering, b2 neutral, b0 closed throttle, b5 rear-defrost load, b7 always 1. Start signal untested | `3.17-bits2`, `3.17-bits-slow` |
| 3.18 | Bits `1E` | ◐ | b6 fuel pump relay *(inferred)*; b1 and b7 on with A/C (which is relay vs fan: open). No fan bit up to 92 °C | `3.17-bits2`, `3.x-drive` |
| 3.19 | Bits `1F` | ◐ | b0 on ~0.2 s during a throttle blip | `3.17-bits2` |
| 3.20 | Bits `21` | ✅ | b7 = `09` lean, b6 = `0A` lean (< ~450 mV). b0 latches on after warm-up. b5/b4 always 1 | `3.17-bits2`, `3.x-drive` |
| 3.21 | Unscaled registers | ☐ | Candidates in `ROM_ANALYSIS.md` §2 | |
| 3.22 | Knock fail-safe state | ✅ | KOER warm idle (2026-11-15): **not latched**, 2nd CPU knock OK, `$0DB8` +0 (`070D=00 0213=88`). P0325 still stored (starts 1), so intermittent or old | `3.22-knock`, `3.22-dtc` |

## 4. Engine active tests (KOER, parked, warm)

Echo `F5 t v`. While held, the ECU streams `FF 00`; `30` → `CF` ends the test.

| # | Test | | Result | Log |
|---|---|---|---|---|
| 4.1 | `81` fuel trim | ☐ | ROM clamps to `4B–7D` (75–125 %) | |
| 4.2 | `82` timing | ☐ | | |
| 4.3 | `84` AAC | — | Not supported (no descriptor); IACV is `85` | |
| 4.4 | `88` power balance | ◐ | `01` cuts cylinder 1 (RH injector time drops). Bitmask vs number: open | `4.4-cut-cyl1` |
| 4.5 | `89` fuel pump | ☐ | | |
| 4.6 | `80` coolant override | ☐ | | |
| 4.7 | `93` / `94` fans | ✅ | Fan runs. Set as a pair (`ROM_ANALYSIS.md` §4) | `4.7-fan-low`, `4.7-fan-high` |
| 4.8 | `8B` clear self-learn | ☐ | | |

## 5. Memory (`C9`, engine)

| # | Test | | Result | Log |
|---|---|---|---|---|
| 5.1 | Single byte | ✅ | `C9 80 00 F0` → `36 80 00`, `FF 01 xx`. 8 addresses per request work, ~55 ms each | `5.1-mem` |
| 5.2 | 9 addresses | ☐ | ROM allows 20 | |
| 5.3 | ROM dump `8000–FFFF` | ✅ | 238 s, sha256 `eb23a73a…615b` | `5.3-rom-dump` |
| 5.4 | Repeat dump | ✅ | Byte-identical | `5.4-rom-dump2` |
| 5.5 | Below `8000` | ✅ | `0080–0FFF` RAM, `1000–2FFF` tables, `3000–3BFF` zeros, `3C00–` code. `5D40–623F` is forwarded to the second CPU, so the dump has a hole there | `5.5-rom-dump-low`, `5.5-ram` |
| 5.6 | Compare with ECUTalk | ☐ | | |
| 5.7 | Second CPU memory | ☐ | `python -m consult sub-dump` | `5.7-sub` |

## 6. Other units

| # | Test | | Result | Log |
|---|---|---|---|---|
| 6.1 | A/T at `EA` | — | No reply (manual car) | `6.2-init-scan` |
| 6.2 | Init scan | ✅ | `DA`→`25` BCM, `DC`→`23` airbag, `E7`→`18` ABS, `ED`→`12` engine. Every reply is `~ID` | `6.2-init-scan` |
| 6.3 | Scan KOER / ASCD on | ☐ | ASCD unit not found yet | |
| 6.4 | Identify units | ✅ | `DA` 28491-2L900 (BCM), `E7` 47850-0L701 (ABS), `DC` airbag (register `AC` = `6B`, the FSM discriminated no.) | `6.4-id-DA`, `6.4-id-E7`, `6.4-id-DC` |
| 6.5 | A/T data | — | Manual car | |

## 7. BCM inputs (`DA`)

Reference: [`BCM.md`](BCM.md).

| # | Test | | Result | Log |
|---|---|---|---|---|
| 7.0 | Find the BCM | ✅ | `DA`, answers with the ASCD switch off | `7.0-DA-main-off` |
| 7.1 | `D0` / `D1` | ✅ | `D0` 20 bytes ending `2L900`; `D1` → `FE` | `6.4-id-DA`, `8.0-cmd-probe-DA` |
| 7.2 | Create a known fault | ☐ | | |
| 7.3 | `C1` erase | ☐ | | |
| 7.4 | Stream all | ✅ | `9E` (echo `61`) = switch block; `9F` not supported | `8.0-cmd-probe-DA` |
| 7.5 | Item scan | ✅ | Reads `02 12 15 19 1A 1B 22 25 2B 35 3B 52 62 72 82 92 B2 C2 E2 F2 FF`, 1–18 bytes each | `7.5-reg-scan-DA` |
| 7.6 | Switch mapping | ◐ | Ignition, ACC (0.7), key in (1.3; slow LOCK→ACC→ON→out run), DR/AS doors, rear doors (only the shared 0.0), trunk (5.4), lock switch, lighting 1st, wiper INT, washer (4.5), all window switches, window lock. High beam, passing, hazard: not in the block. Remote: byte 14 only (LOCK → `1F`, first UNLOCK → `1D`). Byte 14 lock bits: 1 driver, 2 passenger, 3 RR, 4 RL. Hood: open | `7.6-watch-DA-FF`, `7.6-watch-DA-windows`, `7.6-switches-2`, `7.6-lockstate`, `7.6-doorknobs` |
| 7.7 | Wiper knob | ◐ | Switch block byte 17, `01`–`E4`. kΩ fit: open | `7.6-watch-DA-FF` |
| 7.8 | BCM vehicle speed | ☐ | | |
| 7.9 | Mode II cross-check | ☐ | | |
| 7.10 | Side effects while connected | ☐ | | |
| 7.11 | Sleep | ◐ | 2026-11-15: a `5A FF` stream **kept running with the key out** (~4 min) and the BCM ignored `30` (4 tries, no ack); key ON → `30` → `CF` at once. A new init with the key out gets no reply (3 tries). Whether the stream ends by itself, and battery drain: open | `7.6-switches-2`, `7.11-keyoff`, `7.11-stop-keyon`, `7.11-keyout-wake` |

## 8. BCM outputs (`DA`)

Full table: [`BCM.md`](BCM.md), Active tests.

| # | Test | | Result | Log |
|---|---|---|---|---|
| 8.0 | Command / item / value probe | ✅ | `x3` = active test; every value byte echoes | `8.0-cmd-probe-DA`, `8.0-argscan-DA`, `8.0-valscan-DA` |
| 8.1 | `C9` | ✅ | RAM only: `FA00–FCFF`, `FF00–FF64`; 6 addresses per request. No ROM | `8.1-c9scan-DA`, `8.1-bcm-dump` |
| 8.2 | Lamps | ◐ | Room lamp `93 01`, step lamp `E3 01/02`. Illumination, security indicator: open | `8.x-fire-DA` |
| 8.3 | Chime | ◐ | `73/83/B3 01` each chime; all three sound the same. Inferred from the read items: `73` key, `83` light, `B3` seat belt (`B2` bit 2 = belt, `82` bit 1 = lighting switch, `72`/`82` bit 3 = driver door). Key off drops the link, so not confirmed | `8.x-fire-DA`, `8.3-chime-reads`, `8.3-chime-reads-2` |
| 8.4 | Hazard, defogger, wipers | ✅ | Hazard `03 04` / `C3 04`, defogger `63 01`, wipers `53 01` | `8.x-fire-DA` |
| 8.5 | Door locks | ✅ | `23 00` locks while held, unlocks on stop. No per-door value | `8.x-fire-DA`, `gui` |
| 8.6 | Windows | ✅ | `13 01`–`08`: DR, AS, RR, RL × up/down | `8.x-fire-DA` |
| 8.7 | Alarm / starter interrupt | ◐ | Alarm (horn + headlights) `C3 01`. Starter interrupt not found (not `F3 01`) | `8.x-fire-DA` |

## 9. ASCD (cruise)

| # | Test | | Result | Log |
|---|---|---|---|---|
| 9.1 | Find it | ☐ | | |
| 9.2 | Switch inputs | ☐ | | |
| 9.3 | Road test | ☐ | | |

## 10. Airbag (`DC`), read-only

| # | Test | | Result | Log |
|---|---|---|---|---|
| 10.1 | Identify | ✅ | `D0` = `12 A0`. Consult puts the unit in diagnosis mode: the AIR BAG lamp flashes until key off. Registers `8A 8B 9A AB` all `20`, `AC` = `6B`. **Send nothing else** | `6.4-id-DC`, `7.5-paced-DC` |

## 11. Hardware (key off, battery disconnected)

| # | Test | | Result |
|---|---|---|---|
| 11.1 | Photograph the ECU board | ☐ | |
| 11.2 | ROM type (EPROM or internal) | ☐ | Needed to read `5D40–623F` |
| 11.3 | Chip markings | ☐ | CPU variant unconfirmed |
| 11.4 | Trace the Consult pins | ☐ | |

## 12. ECUTalk capture

| # | Test | | Result |
|---|---|---|---|
| 12.1 | Body units in ECUTalk? | ☐ | |
| 12.2 | USB capture of every menu | ☐ | |
| 12.3 | ROM dump sequence | ☐ | |
| 12.4 | Undocumented command bytes | ☐ | |
