# Contributing to open-consult

Reports from other Consult-I cars are welcome, even if the software cannot yet
talk to every module on your car. Bug reports, corrections to the protocol notes,
and code fixes are welcome too.

## Report another car

Follow [Bring up open-consult on another car](NEW_VEHICLE.md) for an ordered,
read-only starting sequence and example scan commands.

Start a [vehicle report](https://github.com/power-emma/open-consult/issues/new/choose)
or copy [`docs/vehicles/TEMPLATE.md`](docs/vehicles/TEMPLATE.md) into a new file
named `docs/vehicles/<year>-<model>-<engine>.md` and open a pull request. Include:

- Year, market, model/chassis, engine, transmission, and ECU or module part
  numbers. Avoid posting VINs, registration numbers, or other personal details.
- Cable and operating system, the command you ran, and the relevant raw TX/RX
  bytes or a redacted log. Say whether the result was observed on the car, read
  from a manual, or inferred from another model.
- Which units replied to init and ID requests, which commands or registers
  worked, and which did not. Record the engine state (key on/engine off,
  running, etc.) where it matters. Do not call a car supported based on its
  model year alone.
- Any differences from the 1998 Maxima results in `README.md`, `BCM.md`, and
  `CAR_TEST_CHECKLIST.md`.

You can start with a partial report and update it as you learn more. Keep each
vehicle's observations in its own file so later contributors can compare them.

## Fix code or documentation

Open an issue for a reproducible bug, or send a focused pull request. Explain
the affected vehicle and ECU identity, expected and actual behavior, and how
you verified the change. Add or update a test when changing protocol decoding,
command behavior, or a confirmed vehicle-specific value. Keep unverified
interpretations labelled as such.

For Python changes, run `python3 -m unittest discover -s tests -p 'test_*.py'`.
For the GTK app, run `make` if GTK 4 and JSON-GLib development packages are
installed, and describe any manual checks in the pull request. Mention checks
you could not run.

## Vehicle safety and shared data

Read the [safety notes](README.md#safety) before using hardware. Begin with
read-only identification and logging; do not run active tests or memory writes
just to complete a report. Never run ABS active test `0A`, and keep the airbag
unit read-only as documented there.

Raw logs may include identifying information. Review and redact them before
posting. Do not add service manuals, commercial ROM packs, proprietary binaries,
or other third-party material without permission. A description of the source
and independently observed bytes is usually enough.

Contributions to the project's original code and documentation are submitted
under the [MIT License](LICENSE). Manuals, ROM images, and other third-party
reference material already in the repository retain their original rights.
