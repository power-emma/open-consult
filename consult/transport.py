"""Serial transport for the Consult dongle: raw 9600 8N1, read timeouts, and a
timestamped log of every TX/RX byte (CAR_TEST_CHECKLIST.md: "log every session raw").

On Linux it uses the standard library only (termios). On Windows it needs pyserial
(`pip install pyserial`); pass the port as e.g. `--dev COM4`.
"""
import datetime
import os
import time

if os.name == "nt":
    import serial
else:
    import fcntl
    import select
    import struct
    import termios

DEFAULT_DEV = "COM4" if os.name == "nt" else "/dev/ttyUSB0"


class Transport:
    def __init__(self, dev=DEFAULT_DEV, log_path=None):
        self.dev = dev
        if os.name == "nt":
            # Same as .NET SerialPort defaults, which ECUTalk relies on: DTR and RTS off.
            self.port = serial.Serial()
            self.port.port, self.port.baudrate, self.port.timeout = dev, 9600, 0
            self.port.dtr = self.port.rts = False
            self.port.open()
        else:
            self.fd = os.open(dev, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
            self._configure()
        self.t0 = time.monotonic()
        self.log = open(log_path, "a") if log_path else None
        self.note(f"open {dev} at {datetime.datetime.now().isoformat(timespec='seconds')}")

    def _configure(self):
        # Raw mode, 9600 8N1, no flow control (CONSULT_PROTOCOL.md §2).
        attrs = termios.tcgetattr(self.fd)
        iflag, oflag, cflag, lflag, ispeed, ospeed, cc = attrs
        iflag = 0
        oflag = 0
        lflag = 0
        # No HUPCL, so closing the port doesn't toggle DTR either.
        cflag = termios.CS8 | termios.CREAD | termios.CLOCAL
        cc[termios.VMIN] = 0
        cc[termios.VTIME] = 0
        termios.tcsetattr(self.fd, termios.TCSANOW,
                          [iflag, oflag, cflag, lflag, termios.B9600, termios.B9600, cc])
        # Linux raises DTR and RTS on open; drop them to match the Windows path (and
        # .NET SerialPort / ECUTalk), which is the setup verified on the car.
        fcntl.ioctl(self.fd, termios.TIOCMBIC,
                    struct.pack("I", termios.TIOCM_DTR | termios.TIOCM_RTS))
        termios.tcflush(self.fd, termios.TCIOFLUSH)

    def _ts(self):
        return time.monotonic() - self.t0

    def _write_log(self, tag, text):
        if self.log:
            self.log.write(f"{self._ts():10.6f} {tag} {text}\n")
            self.log.flush()

    def note(self, text):
        """Free-text line in the log, e.g. what the operator just did."""
        self._write_log("##", text)

    def write(self, data: bytes):
        self._write_log("TX", data.hex(" "))
        if os.name == "nt":
            self.port.write(data)
            self.port.flush()
        else:
            os.write(self.fd, data)
            termios.tcdrain(self.fd)

    def _read_chunk(self, n, timeout):
        if os.name == "nt":
            self.port.timeout = timeout
            return self.port.read(n)
        r, _, _ = select.select([self.fd], [], [], timeout)
        return os.read(self.fd, n) if r else b""

    def read(self, n, timeout=0.5) -> bytes:
        """Read up to n bytes, giving up `timeout` seconds after the last byte arrived."""
        buf = bytearray()
        while len(buf) < n:
            chunk = self._read_chunk(n - len(buf), timeout)
            if not chunk:
                break
            self._write_log("RX", chunk.hex(" "))
            buf += chunk
        return bytes(buf)

    def drain(self, quiet=0.2, limit=3.0) -> bytes:
        """Read everything until the line has been silent for `quiet` seconds."""
        buf = bytearray()
        end = time.monotonic() + limit
        while time.monotonic() < end:
            chunk = self.read(256, timeout=quiet)
            if not chunk:
                break
            buf += chunk
        return bytes(buf)

    def close(self):
        self.note("close")
        if os.name == "nt":
            self.port.close()
        else:
            os.close(self.fd)
        if self.log:
            self.log.close()
