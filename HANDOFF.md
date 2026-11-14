# Handoff: 2026-11-14 bring-up, Windows → Linux

**Goal:** run `consult` on Linux against the 1998 Maxima (manual gearbox, VQ30DE,
ECU 23710-2L904).

**Where it stands:** on Windows the link works end to end with the Python tool:
init, `D0`, `D1`, stop, live streaming, and a 73-register scan. The tool now has
everything this ECU needs, and none of it is Windows-specific. Linux hasn't been
re-tested since these fixes.

## First thing to do on Linux

```
python -m consult --dev /dev/ttyUSB0 --test-id 1.1-linux init
```

Key at ON, nothing else holding the port. Expect:

```
init ok: id ED, attempt 1, 12 after ~15 ms, other bytes first: 00 00
```

Then run `id` (should give `23710-2L904`), `dtc`, `stop-ack`, and
`watch rpm coolant battery tps -n 20`.

If init still fails on Linux, compare the new log line by line with
`logs/2026-11-14_1.1-win-py.log`. Both are written by the same tool, so they should
match byte for byte.

## Why Linux was silent this morning (probable)

1. **Wrong init ID.** This ECU answers **`ED`** (reply `12`), not `EF`. The Linux
   tool sent only `FF FF EF`.
2. **A wrong-ID init locks the ECU.** After `FF FF EF` it sends `00 00` once, then
   **ignores everything, including `30`**, until it gets a correct `ED` init. That
   matches the Linux logs: every `30` and `EF` went unanswered.
   (`logs/2026-11-14_1.1-win-spaced-2.log` shows it on Windows.)
3. **ECUTalk under Wine never sent an init.** Its connect does `TX 30`, then
   `ReadByte()` until `CF` with a 1 s timeout. Under Wine the timeout never fired:
   `logs/2026-11-14_12.2-ecutalk.log` shows `TX 30` followed by status polling until
   it was killed. So it never reached its `EF` → `ED` fallback.

One gap: Linux never saw even the single `00 00` that a first wrong-ID init gets.
Possible reasons: the key was at ACC for the early tests, or the ECU was already
locked. If `ED` works on Linux, that question no longer matters.

## Protocol facts for this ECU (all from logs dated 2026-11-14)

- **Init:** `FF`, wait 280 ms, `FF`, wait 70 ms, `ED` → `00 00 12`. The gaps are
  ECUTalk's (`Delay1`/`Delay2`). `init()` uses them by default; `gaps=None` sends
  the bytes back to back. Whether the gaps matter is **still untested** (checklist 1.3).
- **Stop:** `30` → `CF` (~94 %) or **`FE`** (~6 %). Both happen. Only whole frames
  come before the ack.
- **Command quirks**, both handled automatically by `Consult.command()` with 2 retries:
  - A valid command sometimes gets `FE FE` in place of its first echo pair.
  - A perfect echo is sometimes followed by `FE` in reply to `F0`, with no frames.
    This happens most often with single-register requests: `08` alone nearly always
    does it, and `04`/`37`/`46` sometimes do. Stream them alongside other registers.
- **Unsupported register:** echo `A5 FE`.
- **`D0`** (echo `2F`): a 32-byte frame ending in ASCII `2L904`. `part_number()`
  decodes it.
- **`D1`:** `21 01 34 03 A8 00`, i.e. stored codes 21 (ignition signal?), 34 (knock?)
  and **A8 (unknown)**.
- **Supported registers (73):** `00–05 08–0D 10 11 13–16 18 1A–23 28–2A 30–35 37–3F
  40–47 49 4A 4C 4E 4F 51 56–61`, with `04 37 46` only reliable in multi-register
  streams. **`17` (AAC) is not supported.** Details: checklist 3.1.
- **Scalings confirmed on the car:** RPM `00/01` × 12.5 (matches the tach at 2000 and
  2500), battery `0C` × 80 mV, coolant/IAT − 50, TPS × 20 mV, MAF × 5 mV, O2 × 10 mV,
  injector `14/15` and `22/23` / 100 ms, timing 110 − v, alpha %.
  **CAS `02/03` × 8 is not RPM** (it reads about 14 × RPM); still unresolved.
- **Bit registers** (bit 7 = MSB; summary also in `registers.py`):
  - **`13`:** b4 A/C switch, b3 power steering, b2 neutral (1 = N), b5 rear
    defrost, b0 closed throttle. b7 is always 1.
  - **`1E`:** b6 fuel pump relay (probably). b1 and b7 come on with A/C (which is
    the relay and which a fan is still open).
  - **`1F`:** b0 pulses briefly on a throttle blip.
  - **`21`:** b7 and b6 are the O2 rich/lean bits, one per bank.
  - Headlights, hazards and the heater blower don't appear.
- **Throughput:** ~39 frames/s with 19 registers on Windows FTDI default latency.
  Linux has latency_timer = 1 via udev, so compare (checklist 3.4).

## Dongle

- FT232R `0403:6001`, serial `A7AHY3Q8`. Its EEPROM is factory default.
- **It dropped off USB twice today:** on Linux 8 s into a test (11:26:38), and on
  Windows 9 s into a KOER capture (`logs/2026-11-14_3.17-bits.log`). Replugging
  fixed it both times. The cause is unknown: possibly cable movement, the USB port,
  or the dongle's power. On Linux, watch `dmesg -w` during long captures.
- The udev rule from this morning (`/etc/udev/rules.d/99-consult.rules`) should still
  apply: mode 0666, `/dev/consult` symlink, latency_timer 1.

## ECUTalk 1.5.0 (decompiled on Windows, for reference)

Dotfuscator-obfuscated .NET, read by reflection with `tools/ildump.ps1`:
- `SerialPort` defaults (9600 8N1, DTR/RTS off), with 1000 ms timeouts.
- Connect: open, stop, init(ini ECUID = `EF`), init(the other ID) if that fails, stop.
- Stop: `30`, then ReadByte until `CF`, then Sleep(FlushWait).
- Init: `FF`, Sleep(Delay1), `FF`, Sleep(Delay2), `<id>`, then poll 13 × 100 ms for `~id`.
- `ECU_ID` enum: `EF` Normal, `ED`, `E5` Active Suspension.
- Register table: water temp `08`, injector `14/15`, injector RH `22/23`.

## Code changes this session (uncommitted)

- `consult/protocol.py`:
  - `init()` uses the ECUTalk byte gaps, tries `ED` then `EF`, and returns the ID
    that answered.
  - `command()` retries on `FE FE` echoes and on `F0` → `FE`.
  - `part_number()` decodes the ASCII part number.
- `consult/__main__.py`: `--ecu XX` (repeatable). A busy port on Windows now gives a
  "close ECUTalk" message instead of a traceback.
- `consult/registers.py`: added `cas_rpm`, `inj_rh`, `bits20`, `bits21`, plus bit-map
  notes. `aac` is marked as not on this car.
- `tools/init-probe.ps1`, `tools/ildump.ps1`: Windows-only helpers.
- `CAR_TEST_CHECKLIST.md`: results for 0.7, 1.1, 1.5, 2.1, 2.3, 2.7, 3.1–3.8, 3.10,
  3.11, 3.13, 3.14, 3.16–3.20.
- `logs/2026-11-14_*`: every Windows session. **Ignore
  `2026-11-14_1.1-win-spaced-after-ecutalk.log`**: ECUTalk held the port during that
  run, so it's meaningless. In the earliest PowerShell probe runs the console output
  hid RX lines, but the log files themselves are correct.

## Next steps (Linux)

1. Run `init`, `id`, `dtc`, `stop-ack` and `watch` as above. Fill in the checklist with
   `-linux` test IDs.
2. Checklist 1.3: run init without gaps (`Consult.init(gaps=None)`).
3. Checklist 3.4: frame rate at latency_timer 1 vs 16.
4. Identify DTC `A8`: compare with `EL.pdf` and a generic OBD-II scan (2.3/2.7).
5. Then sections 4 (active tests) and 5 (ROM read), in checklist order.

## Tools

- `python -m consult {init,stop-ack,id,dtc,watch,reg-scan}` (add `--ecu XX` to pick
  the init ID): read-only, logs to `logs/`.
- `tools/serlog.c`: an `LD_PRELOAD` serial logger for Wine apps
  (`gcc -shared -fPIC -o serlog.so serlog.c -ldl`, then
  `SERLOG=log LD_PRELOAD=./serlog.so wine app.exe`).
- `tools/init-probe.ps1` / `tools/ildump.ps1`: Windows PowerShell only.
