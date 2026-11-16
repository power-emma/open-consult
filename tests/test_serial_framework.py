"""POSIX I/O checks plus a reproducible short-write regression.

PTY setup bypasses cable modem-control configuration, which PTYs do not support.
The read/write methods under test are the production Transport methods.
"""
import os
import errno
import select
import sys
import time
import unittest
from unittest.mock import patch


@unittest.skipUnless(sys.platform.startswith("linux"), "Linux PTY backend test")
class SerialFrameworkTests(unittest.TestCase):
    def setUp(self):
        import pty
        import tty
        from consult.transport import Transport
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        tty.setraw(slave)
        os.set_blocking(slave, False)
        self.master = master
        self.transport = Transport.__new__(Transport)
        self.transport.fd = slave
        self.transport.log = None
        self.transport.t0 = time.monotonic()

    def test_production_io_over_real_pty(self):
        data = bytes(range(256))
        os.write(self.master, data)
        self.assertEqual(self.transport.read(len(data), timeout=0.1), data)
        self.transport.write(b"\xc9\x10\x00")
        readable, _, _ = select.select([self.master], [], [], 0.2)
        self.assertTrue(readable)
        self.assertEqual(os.read(self.master, 32), b"\xc9\x10\x00")

    def test_regression_partial_os_write_must_send_remaining_suffix(self):
        accepted = bytearray()

        def short_write(fd, data):
            count = min(2, len(data))
            accepted.extend(data[:count])
            return count

        with patch("consult.transport.os.write", side_effect=short_write):
            self.transport.write(b"\xc9\x10\x00\xf0")
        self.assertEqual(accepted, b"\xc9\x10\x00\xf0")

    def test_failed_suffix_retains_confirmed_prefix(self):
        from consult.hardening import WriteFailure
        with patch("consult.transport.os.write", side_effect=[2, OSError(errno.EIO, "lost")]):
            with self.assertRaises(WriteFailure) as caught:
                self.transport.write_all(b"\xc9\x10\x00\xf0", deadline=time.monotonic() + 1)
        self.assertEqual(caught.exception.result.accepted, 2)

    def test_zero_progress_is_not_success(self):
        from consult.hardening import WriteFailure
        with patch("consult.transport.os.write", return_value=0):
            with self.assertRaises(WriteFailure):
                self.transport.write_all(b"\xf0", deadline=time.monotonic() + 1)
