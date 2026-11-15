# BCM (IVMS body control module): Consult reference

1995–99 Nissan Maxima (A32), BCM 28491-2L900. All values were observed on a 1998 car,
except entries marked *inferred* or *open*.

## Unit

| | |
|---|---|
| Init | `FF FF DA` → `25` |
| Part number | 28491-2L900 ("Controller Assy-LAN"), `D0` ends ASCII `2L900` |
| `D0` frame | `25 13 00 07 1F 00 01 01 3A D3 DF 01 70 01 50 32 4C 39 30 30` |
| Consult pins | BCM 39 (TX) → connector pin 2, BCM 40 (RX) → connector pin 1. No clock line |
| Fuses | BAT 7.5 A #56, ACC 7.5 A #19, IGN 7.5 A #12 |
| Needs | Ignition ON (the Consult connector's power pin is IGN-fed) |

Other units on the same connector: `ED` engine, `DC` airbag, `E7` ABS.

## Link rules

1. Send **one byte at a time**, and send the next byte only after its echo arrives.
   A burst gets `FE`.
2. **One `5A` item per request.** A second item gets `FE`.
3. **`C9`: at most 6 addresses per request.**
4. Frame length depends on the item (1–18 bytes). Parse by the length byte.
5. Stop: `30` → `CF`.
6. Cranking drops the link (no stop ack). Don't hold a test through START.

## Commands

| Cmd | Echo | Use |
|---|---|---|
| `5A <item>` | `A5 <item>` | Read item |
| `9E` | `61` | Stream all (same 18-byte block as `5A FF`) |
| `C9 <hi> <lo>` | `36 <hi> <lo>` | Read RAM |
| `D0` | `2F` | Part number |
| `0A <item> <value>` | `F5 <item> <value>` | Active test |
| `D1`, `9F` | `FE` | Not supported |
| `C1` | | Untested (probably erases the stored IVMS results) |

## Item numbering

Item byte = `<group><op>`. **op `2` = read, op `3` = active test.**

| Group | Function |
|---|---|
| `0` | Trunk / hazard / panic |
| `1` | Power windows |
| `2` | Door locks |
| `5` | Wipers |
| `6` | Rear defogger |
| `7` `8` `B` | Chime |
| `9` | Room lamp |
| `C` | Horn + headlights (alarm) |
| `E` | Step lamps |
| `F` | *open* (illumination, *inferred*) |

## Read items (`5A`)

Values at rest, key ON, doors shut.

| Item | Bytes | Value at rest | Streams |
|---|---|---|---|
| `FF` | 18 | `80 0A 00 00 00 08 00 00 00 00 00 00 00 00 01 00 40 04` | yes (switch block) |
| `02` | 2 | `02 80` | yes |
| `12` | 3 | `00 02 20` | yes |
| `22` | 3 | `06 00 00` | yes |
| `52` | 2 | `02 04` | yes |
| `C2` | 3 | `14 00 08` | yes |
| `62` `72` `82` `92` `B2` | 1 | `04` `06` `04` `01` `06` | one frame |
| `E2` `F2` | 1 | `00` `00` | one frame |
| `15` `25` `35` | 18 | all `00` | yes |
| `1B` `2B` | 16 | all `00` | yes |
| `19` `1A` `3B` | 2 | all `00` | yes |

What the `x2` items and the other reads hold is *open*.

## Switch block (`5A FF` / `9E`)

Byte 0 = first data byte. Bit 7 = MSB.

| Byte | Bit | Input |
|---|---|---|
| 0 | 7 | ACC (key at ACC or ON) |
| 0 | 0 | Any door open (the only bit for the rear doors) |
| 1 | 1 | Ignition ON |
| 1 | 3 | Key in ignition |
| 2 | 6 | Driver lock switch: LOCK |
| 2 | 7 | Driver lock switch: UNLOCK |
| 4 | 0 | Lighting switch 1st position |
| 4 | 4 | Wiper INT switch |
| 4 | 5 | Washer switch |
| 4 | 7 | Driver door |
| 5 | 4 | Trunk open |
| 12 | 0 | Passenger window UP (master) |
| 12 | 1 | Passenger window DOWN (master) |
| 12 | 2 | Rear LH window UP (master) |
| 12 | 3 | Rear LH window DOWN (master) |
| 12 | 4 | Rear RH window UP (master) |
| 12 | 5 | Rear RH window DOWN (master) |
| 12 | 6 | Window lock |
| 12 | 7 | Passenger window UP (passenger switch) |
| 13 | 0 | Passenger window DOWN (passenger switch) |
| 13 | 5 | Driver window UP |
| 13 | 6 | Driver window DOWN |
| 13 | 7 | Driver window AUTO (set together with bit 6) |
| 14 | — | Door lock state, bit set = locked: bit 0 always 1, bit 1 driver, bit 2 passenger, bit 3 rear RH, bit 4 rear LH (`01` all unlocked, `1F` all locked). Doors report a few tens of ms apart as the actuators move |
| 16 | 5 | Passenger door |
| 16 | 6 | Seat belt *(inferred)* |
| 17 | — | Intermittent wiper knob, analog `01`–`E4` |

The rear doors only set byte 0 bit 0. Headlights 2nd position (only the 1st-position bit
sets), high beam, flash-to-pass and the hazard switch show up nowhere in the block
(`7.6-switches-2`, 2026-11-15). Byte 17 jitters ±1 count at rest.

The keyless remote shows only as a byte 14 change (no button bit): LOCK → `1F`, first UNLOCK → `1D` (driver only).
Byte 14 bits from the inside knobs (`7.6-doorknobs`): each rear knob moves only its own bit
(`09` RH, `11` LH). The passenger knob locks all four doors but unlocks only its own (`1F → 1B`).
The driver bit is the one left (and the remote's first unlock clears it).

Not located yet: hood, defogger switch, key cylinder, unlock sensors.

## Active tests (`0A <item> <value> F0`)

Sequence (paced): `0A` → `F5`, item → item, value → value, `F0`. The output runs
**only while the test is held**; `30` → `CF` ends it.

- Frames while running: items `03` and `13` stream `FF 01 vv`, item `23` streams
  `FF 02 01 3E`, all others stream `FF 00`.
- **Every value byte is echoed.** An invalid value is accepted but does nothing
  (empty frames).

| Item | Value | Output |
|---|---|---|
| `03` | `03` | Trunk release |
| `03` | `04` | Hazard lamps (steady) |
| `03` | `06` | Panic (horn + lights) |
| `13` | `01` / `02` | Driver window up / down |
| `13` | `03` / `04` | Front passenger window up / down |
| `13` | `05` / `06` | Rear right window up / down |
| `13` | `07` / `08` | Rear left window up / down |
| `23` | `00` | All doors lock while held, unlock on stop |
| `53` | `01` | Wipers |
| `63` | `01` | Rear defogger |
| `73` `83` `B3` | `01` | Chime (key / light / seat-belt warning, order *open*) |
| `93` | `01` | Room lamp |
| `C3` | `01` | Horn + headlights |
| `C3` | `04` | Hazard lamps |
| `E3` | `01` | Step lamp LH *(inferred)* |
| `E3` | `02` | Step lamp RH |

Window value = `1 + 2 × window + down`, with window 0–3 = driver, passenger, rear
right, rear left.

**No visible effect:** `03` with `01 02 05`; `C3` with `02 03 05`–`08`; `F3` with
`01`–`08`. **Invalid:** `03` with `07`–`10`; `13` with `10 20 40 80`; `23` with `01`–`08`.

**Not found yet:** starter interrupt relay (not `F3 01`), security indicator lamp,
illumination lamp, single-door lock motors. `0A` also echoes the items
`05 09 0A 11 1B 3B FE` (function *open*).

## Memory (`C9`)

| Range | Contents |
|---|---|
| `FA00–FCFF` | Work RAM (ASCII `L-A- Network` at `FAD0`) |
| `FF00–FF64` | I/O / flags |
| `FD00–FEFF` | Not scanned |
| everything else | Rejected (`FE` on the low byte) |

The program ROM can't be read over Consult.

## Rules

1. Never send anything but `D0`/`D1` to `DC` (airbag). Never send `0A` to `E7` (ABS).
2. Windows: hold-to-run only, hands clear.
3. Door lock test: keep a door open and the key out of the ignition.
4. Don't send `C1` unless you mean to erase the IVMS memory.
5. While Consult is connected, some IVMS functions are suspended (FSM EL-168).

## Tools

| Task | Command |
|---|---|
| Identify | `python -m consult --ecu DA id` |
| Watch switches | `python -m consult bcm-watch` |
| Watch RAM | `python -m consult --ecu DA watch-mem FA00 -n 96` |
| Run a test | `python -m consult bcm-test <name> [--hold s]` |
| Scans | `tools/bcm/argscan.py`, `valscan.py`, `c9scan.py`, `fire2.py` |
| GUI | `consult-gui`, BCM tests tab |

## Open

- Starter interrupt, security indicator, illumination: item and value.
- Chime item → warning mapping.
- Meaning of the `x2` items and items `15 19 1A 1B 25 2B 35 3B`.
- Remaining switch-block inputs (see above).
- IVMS COMM / WAKE-UP diagnosis commands.
- Behaviour with the key off. Seen 2026-11-15: an open stream keeps running with the key
  out and ignores `30` until the key is back ON; a new init with the key out gets no
  reply. **End sessions with the key ON.** Does the stream ever stop by itself?
