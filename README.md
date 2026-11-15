# open-consult

An open, Linux-first replacement for Nissan's Consult-I diagnostic tools, built on a
**1998 Nissan Maxima (A32, VQ30DE, 5-speed)** with a cheap FTDI Consult-to-USB cable.
It reads live engine data, reads and clears fault codes, runs active tests, dumps the
engine ROM, and **talks to the body control module**.

## First to crack the IVMS body control module

As far as I can find, **nobody outside Nissan's own CONSULT hand-held has ever
published how to talk to the A32's IVMS body control module.** Every open-source
Consult project in the past and every protocol document stops at the engine ECU,
the A/T unit, HICAS and A/C. The service manual gives the item names but not one byte. 
(Search done 2026-11-15; if you know of earlier work, please tell me and i will credit it.)

Starting from nothing but the service manual and a USB cable, this project:

- **found every Consult unit on the car** by init scan (`ED` engine, `DA` BCM, `DC`
  airbag, `E7` ABS) and identified each one from its part number;
- worked out that the BCM wants commands paced one byte per echo, one read item
  per request, with its own item numbering (`x2` = read, `x3` = active test) and its own
  stream-all command (`9E`);
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
  car and on the road (speed confirmed from gear ratios, the CAS register decoded as a
  crank period), stored codes decoded to OBD-II P-codes, active tests, and a full `C9`
  ROM dump.
- **ROM disassembly** of 23710-2L904 (Mitsubishi 7700): the Consult handler, register
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

# GTK 4 app
make && ./consult-gui
```

The cable shows up as an ordinary 9600 8N1 serial port (`/dev/ttyUSB0`). Set the FTDI
latency timer to 1 ms for smooth data (`CONSULT_PROTOCOL.md` §2).

## Docs

| File | What's in it |
|---|---|
| [`BCM.md`](BCM.md) | The body control module: link rules, items, switch map, active tests |
| [`CONSULT_PROTOCOL.md`](CONSULT_PROTOCOL.md) | The Consult-I protocol, with what this car actually does |
| [`ROM_ANALYSIS.md`](ROM_ANALYSIS.md) | Engine ROM disassembly notes |
| [`VEHICLE_SYSTEMS.md`](VEHICLE_SYSTEMS.md) | Service-manual digest: units, specs, ECM pinout |
| [`CAR_TEST_CHECKLIST.md`](CAR_TEST_CHECKLIST.md) | Every test run on the car, with results and logs |
| [`BODY_DIAG_PLAN.md`](BODY_DIAG_PLAN.md) | Service-manual reference for the IVMS and ASCD, and remaining body work |

## Safety

- **Airbag unit (`DC`): read-only.** Consult switches it into diagnosis mode (the lamp
  flashes). Send nothing beyond `D0`/`D1`.
- **ABS (`E7`): never send `0A`.** Its active tests drive the brake solenoids and pump.
- **Engine active tests change fuel, timing and pumps.** Use them parked, engine warm.
  Don't fire unknown test IDs: on a sister ECU one of them re-registered the immobiliser
  keys.
- **BCM tests move windows and locks.** Keep hands clear
