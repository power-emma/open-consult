# open-consult

An open, Linux-first replacement for Nissan's Consult-I diagnostic tools, built on a
**1998 Nissan Maxima (A32, VQ30DE, 5-speed)** with a cheap FTDI Consult-to-USB cable.
It reads live engine data, reads and clears fault codes, runs active tests, dumps the
engine ROM, and **talks to the body control module**.

## First public write-up of the IVMS Body Control Module

As far as I can find, **nobody outside Nissan's own CONSULT hand-held has ever
published how to talk to the A32's IVMS body control module.** Every open-source
Consult project in the past and every protocol document stops at the engine ECU. The service manual gives the item names but not the bytes.
(Search done 2026-11-15; if you know of earlier work, please tell me and i will credit it.)

Starting from nothing but the service manual and a USB cable, this project:

- **found every Consult unit on the car** by init scan (`ED` engine, `DA` BCM, `DC`
  airbag, `E7` ABS) and identified each one from its part number;
- **worked out BCM command structure**
- **mapped the BCM's 18-byte switch block**: ignition, doors, lock switch, lighting,
  wiper switch and knob, and every power-window switch;
- **drove the body outputs from a laptop**: all four windows, door locks, trunk
  release, hazards, panic, horn + headlights, wipers, rear defogger, interior lamp,
  step lamps and the chime;
- put it all in a GTK app with hold-to-run buttons.

The full write-up is **[`BCM.md`](BCM.md)**, so the next person with an IVMS Nissan
doesn't have to start from zero.

## Also in here

- **Engine ECU, fully probed:** all 73 supported registers with scalings checked on the
  car speed confirmed from gear ratios, the CAS register decoded as a
  crank period, stored codes decoded to OBD-II P-codes, active tests, and a full `C9`
  ROM dump.
- **ROM disassembly** of Mitsubishi 7700: the Consult handler, register
  and active-test tables, fault-code storage, the second CPU, and where the fuel, timing and
  knock maps live. See [`ROM_ANALYSIS.md`](ROM_ANALYSIS.md).
- **Raw logs of every session** in `logs/`, timestamped byte by byte, so every claim in
  the docs can be checked. Logs named `maxine-*` are from the project car; the tools
  name your own logs `YYYY-MM-DD_<test-id>.log`.

## Quick start

```sh
# Python CLI (pyserial). Every run appends a raw TX/RX log to logs/.
python -m consult init                 # engine ECU: FF FF ED -> 12
python -m consult id                   # part number
python -m consult dtc                  # fault codes
python -m consult watch rpm coolant tps speed
python -m consult bcm-watch                # BCM switches, by name
python -m consult bcm-test window-dr-down  # BCM output
python -m consult p1320                    # P1320 monitor
python -m consult knock                    # knock fail-safe state

# GTK 4 app (requires GTK 4 and JSON-GLib development packages)
make && ./consult-gui
```

In the GUI, choose **Log playback → Open log…** to review recorded engine
sensors without a cable. Drag the timeline or use Previous/Next frame to inspect
values. Playback reads the existing raw TX/RX logs, including partial sensor lists;
sensors absent from a frame show a dash. Times start at the first sensor frame.
Body-module and other non-sensor traffic is skipped.

In **Fuel maps**, import a JSON map and choose **Stream map…** with the engine
running. Streaming defaults to **Until stopped**. Uncheck it to set a time limit. The stream targets ECU `23710-2L904`. It looks up each
request using live RPM and the raw ECU load code. **Stop streaming** ends the
session early. The GUI checks both banks and verifies release after sending STOP.
Each session records decoded RPM, load, requested fuel percentage, both banks'
feedback and injector duration, and knock readings in a timestamped
`*_gui-fuel.csv` in the log directory. The daily GUI log retains the raw Consult bytes.

[The stock template](maps/native-fuel-stock.json) uses `fuel_percent` cells in
75–125. You can instead use `fuel_offset_percent` cells in −25 to +25. A +5 offset
sends a native value of 105, a zero offset requests a fixed 100%, and `null`
lets the ECU control feedback. Rows follow `load_code_axis` and columns follow
`rpm_axis`. Lookup interpolates between breakpoints and clamps at the edges.

The **Ignition timing** section on that page shows both factory timing tables
as raw ROM bytes. **Probe timing…** runs a two-second Consult `0x82` test at
stationary idle using a raw byte from `0x00` through `0x03`. The GUI compares ECU-reported timing
before and during the probe and checks override release afterward. The parameter's
units and direction are still unverified for this ECU.

The cable shows up as a 9600 8N1 serial port (`/dev/ttyUSB0`). Set the FTDI
latency timer to 1 ms for smooth data (`CONSULT_PROTOCOL.md` §2).

### Windows

Install [MSYS2](https://www.msys2.org), then in the **UCRT64** shell:

```sh
pacman -S --needed make mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-pkgconf mingw-w64-ucrt-x86_64-gtk4 mingw-w64-ucrt-x86_64-json-glib
make            # consult-gui.exe (runs from the MSYS2 shell)
make dist       # dist/consult-gui-windows/: the .exe plus the GTK DLLs, runs from Explorer
make onefile    # dist/consult-gui.exe: all of it in one file (~27 MB)
```

GTK only comes as DLLs on Windows, so the single-file `.exe` is a small launcher with
the `dist` folder packed inside. Its first run unpacks it to
`%LOCALAPPDATA%\open-consult` (a few seconds); later runs start straight from there, and
a new build replaces the old copy.

The cable is a COM port (`COM4` here); the port list shows each one's Device Manager
name. Logs go to `logs/` next to the `.exe`. Close ECUTalk first: Windows lets only one
program hold the port. For smooth data, set the FTDI latency timer to 1 ms in Device
Manager → the port → Port Settings → Advanced.

## Docs

| File | What's in it |
|---|---|
| [`BCM.md`](BCM.md) | The body control module: link rules, items, switch map, active tests |
| [`CONSULT_PROTOCOL.md`](CONSULT_PROTOCOL.md) | The Consult-I protocol, with what this car actually does |
| [`ROM_ANALYSIS.md`](ROM_ANALYSIS.md) | Engine ROM disassembly notes |
| [`docs/ROM_ATLAS.md`](docs/ROM_ATLAS.md) | Firmware subsystem map, corrected RPM/idle interpretations, and reproducible code/table inventory |
| [`docs/TUNING_PATHS.md`](docs/TUNING_PATHS.md) | Reachable pointers, tuning candidates, and native fuel-control verification tool |
| [`VEHICLE_SYSTEMS.md`](VEHICLE_SYSTEMS.md) | Service-manual digest: units, specs, ECM pinout |
| [`CAR_TEST_CHECKLIST.md`](CAR_TEST_CHECKLIST.md) | Every test run on the car, with results and logs |
| [`BODY_DIAG_PLAN.md`](BODY_DIAG_PLAN.md) | Service-manual reference for the IVMS and ASCD, and remaining body work |

## Contributing

Have another Consult-I car? Start with [NEW_VEHICLE.md](NEW_VEHICLE.md) for
connection checks, read-only scans, and how to record results. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the report template and pull request process.
Partial results are useful; the behavior documented above is confirmed on the
project's 1998 Maxima and should be checked separately on other vehicles.

## Safety

- **Airbag unit (`DC`): read-only.** Consult switches it into diagnosis mode (the lamp
  flashes). Send nothing beyond `D0`/`D1`. Im not trying to get my airbag to explode my laptop into my face.
- **ABS (`E7`): never send `0A`.** Its active tests drive the brake solenoids and pump.
- **Engine active tests change fuel, timing and pumps.** You're going to be turning off cylinders and the like just be smart
- **BCM tests move windows and locks.** Keep hands clear

## ECU RAM write access

The Consult `C9` command can write a byte to ECU working RAM — this is an
authorized diagnostic procedure documented in a Nissan service bulletin.
I reverse-engineered the mechanism independently before finding the bulletin.
See [`write access nissan.md`](write%20access%20nissan.md) for the full
explanation and [`nissan-write.py`](nissan-write.py) for a payload builder /
simulator. Research notes and session logs are in
[`docs/processor-write/`](docs/processor-write/).

## License

The project's original code and documentation are licensed under the
[MIT License](LICENSE). Manuals, ROM images, and other third-party reference
material in the repository (including `fsm/`, `reference/`, and `rom/`) retain
their original rights and are not relicensed by this project.
