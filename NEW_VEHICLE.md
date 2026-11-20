# Bring up open-consult on another car

This is a starting sequence for a **Consult-I car with the 14-pin connector**.
The commands and decoded names in this repository were developed on a 1998
Maxima A32, VQ30DE, manual, ECU `23710-2L904`. Another Nissan may use different
unit IDs, register sets, scalings, frame lengths, and active-test meanings. Treat
its first results as raw observations until you have checked them on that car.

Start with the read-only steps below. A successful `init` is already a useful
contribution; you do not need to complete every scan. Read the [safety notes](README.md#safety)
and [contribution guide](CONTRIBUTING.md) first.

## 1. Record the setup

Copy [`docs/vehicles/TEMPLATE.md`](docs/vehicles/TEMPLATE.md) to
`docs/vehicles/<year>-<model>-<engine>.md`. Record the market, chassis, engine,
transmission, connector, cable, OS, and module part numbers you can read from
labels. Do not publish VINs or registration numbers.

Use a Consult-I USB serial cable, with the car parked, parking brake set, and
ignition on with the engine off (**KOEO**). The serial link is 9600 8N1. On
Linux the default port is `/dev/ttyUSB0`; on Windows install `pyserial` and
pass `--dev COM4` (or your actual COM port). Close other diagnostic programs
that have the port open. See [protocol setup](CONSULT_PROTOCOL.md) §2 if the
link is unstable.

The examples below use the default Linux port. Put `--dev <port>` before the
subcommand when your port differs. Put `--test-id <unique-name>` there too:
each run **appends** to `logs/YYYY-MM-DD_<test-id>.log`, so a new name keeps
experiments separate. Review and redact logs before sharing them.

## 2. Find a responding unit

Try the known engine IDs first. They are defaults from this project, not a
promise that your car uses either one:

```sh
python3 -m consult --test-id mycar-init init
```

If no unit replies, check the ignition, cable, port, and connector before
changing code. You can sweep possible **init IDs** with:

```sh
python3 -m consult --test-id mycar-init-scan init-scan
```

This sends `FF FF <ID>` for IDs `00` through `FF`, logs replies, and skips the
known airbag ID `DC`. It can take several minutes. Its `ID -> response` hits
are candidates, not proof of a module's identity; compare with the service
manual and a part-number response. The scan only excludes `DC`, so stop if
your car's module layout makes a broader scan inappropriate. Record the exact
IDs and raw reply bytes, including failures. If you already know a range, use
`init-scan --first <hex> --last <hex>` to narrow it.

Do **not** address the airbag unit or sweep arbitrary commands on unknown
units. On the project car, `DC` is SRS and `E7` is ABS. The CLI blocks explicit
`--ecu DC` and skips it during `init-scan`.

## 3. Identify the engine ECU and read fault codes

Once you have a likely engine init ID, substitute its two-digit hex value for
`<engine-id>` below. The `--ecu` flag goes before the subcommand:

```sh
python3 -m consult --ecu <engine-id> --test-id mycar-id id
python3 -m consult --ecu <engine-id> --test-id mycar-dtc dtc
```

Save the complete `D0` and `D1` replies, not just the displayed part number or
decoded codes. The code table reflects the project car and may need checking
against your ECU. Do not clear codes as part of the first pass.

## 4. Sweep engine read items

With the engine ECU identified, the `reg-scan` command sends a `5A` read for
each item in the chosen range and reports supported bytes. A first pass is:

```sh
python3 -m consult --ecu <engine-id> --test-id mycar-reg-00-5f reg-scan --first 00 --last 5F -v
python3 -m consult --ecu <engine-id> --test-id mycar-reg-60-ff reg-scan --first 60 --last FF -v
```

Run the second range only after reviewing the first. `-v` records failures as
well as hits. A supported reply only establishes that the ECU answered; its
length and interpretation may differ from the A32. Note stalls, malformed
frames, and whether a repeat gives the same result. Avoid `cmd-probe` and
`raw-cmd` for discovery: those can send commands with unknown effects.

For a short live check on the engine, use a bounded frame count:

```sh
python3 -m consult --ecu <engine-id> --test-id mycar-idle watch rpm coolant battery tps -n 20
```

Run this only for registers confirmed in the preceding scan. `watch` uses A32
register numbers and conversions, so compare the raw log with known values
(tachometer, temperature, meter) before trusting the displayed units. Start
KOEO; repeat at stationary idle (**KOER**) only if the reads behave normally.
If any value looks wrong, document the raw bytes and expected reading rather
than changing a global scaling for every car.

## 5. Other modules: targeted reads only

If the init scan found another unit, identify it from documentation and its
part number before reading more. For example, the project car's BCM uses `DA`:

```sh
python3 -m consult --ecu DA --test-id mycar-bcm-id id
python3 -m consult --ecu DA --test-id mycar-bcm-reg-00-1f reg-scan --first 00 --last 1F -v
```

`DA` is an **example for the A32**, not a default for other cars. Begin with a
small known range, review responses, then extend only if you understand the
module. The `bcm-watch` decoder and `bcm-test` actions are A32-specific; do not
assume their names or outputs apply to your vehicle. Do not use broad register
or command sweeps on SRS or ABS. The project car's SRS must remain read-only,
and ABS active test `0A` operates the brake hardware.

## 6. Share a useful result

In your vehicle file, include a table of each unit's init ID, part number,
working reads, failures, and the log filename. For each result, note KOEO or
KOER, the exact command, TX/RX bytes, and whether the meaning is **observed**,
**from a manual**, or **inferred**. Compare differences with
[`CAR_TEST_CHECKLIST.md`](CAR_TEST_CHECKLIST.md), and propose a code change in a
separate focused pull request when a decoder or command needs to vary by ECU.

Avoid committing full copyrighted manuals, commercial ROM packs, or raw ECU
firmware. A redacted log and a precise description of the finding are enough
to begin a review. If a command times out or the car behaves unexpectedly,
stop that line of testing and report what happened.
