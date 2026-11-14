# Handoff: 2026-11-14 bring-up session (Linux → Windows)

**Where it stands:** the engine ECU sends no bytes at all on Linux. Nothing has ever
come back: no `10` for init, and no `CF` for stop. ECUTalk 1.5.0 run under Wine on
the same port gets the same silence. Checklist results 0.1–0.4 and 1.1 are filled in
`CAR_TEST_CHECKLIST.md`.

## What we know

- The dongle is a generic eBay 14-pin Consult cable: an FT232R with a **factory-default**
  EEPROM, so its CBUS pins output no clock and the board must make its own.
- The key was at ACC for the first tests and at ON for the later ones. Both were silent.
- At 11:26:38, 8 s into a test, the dongle dropped off USB and reconnected.
  The cause is unknown.
- ECUTalk is a .NET app using `System.IO.Ports.SerialPort` with defaults (9600 8N1,
  DTR/RTS off). Settings are in `ecutalk.ini`, which isn't committed: `Delay1:280`,
  `Delay2:70`, `FlushWait:100`, `ECUID:EF`. Its first byte on connect is `30`.
- Captured under Wine: `logs/2026-11-14_12.2-ecutalk.log`. It shows termios set,
  RTS toggled then DTR=RTS=0, flush, `TX 30`, then no RX.

## Next steps (on Windows)

1. Run ECUTalk once without touching the car or the cable. Note whether it connects
   and which COM port it uses.
2. Close ECUTalk, then:
   ```
   pip install pyserial
   python -m consult --dev COM4 --test-id 1.1-win init
   ```
   - **If ECUTalk works but this doesn't:** it's a tool difference. Sniff ECUTalk on
     Windows (e.g. a COM port monitor) and compare it with `logs/`.
   - **If both work:** the problem is in Linux's `ftdi_sio` path. Compare timing and
     modem lines.
   - **If neither works:** it's the cable, the connector seating, or ECU power. Check
     the key at ON, the battery, and that the grey 14-pin plug is fully latched.
3. Continue `CAR_TEST_CHECKLIST.md` from 1.1 with the commands in `consult/__main__.py`.

## Tools

- `python -m consult {init,stop-ack,id,dtc,watch,reg-scan}`: read-only, logs to `logs/`.
- `tools/serlog.c`: an `LD_PRELOAD` logger for capturing a Wine app's serial traffic
  on Linux (`gcc -shared -fPIC -o serlog.so serlog.c -ldl`, then
  `SERLOG=log LD_PRELOAD=./serlog.so wine app.exe`). Wine's COM4 was mapped to
  `/dev/ttyUSB0` via `HKLM\Software\Wine\Ports`.
