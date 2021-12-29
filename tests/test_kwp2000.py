#!/usr/bin/env python3

import unittest
from unittest.mock import Mock

from kwp2000 import KWP2000Client, SESSION_TYPE, NegativeResponseError


class TestKWP2000Client(unittest.TestCase):
    def setUp(self):
        self.transport = Mock()
        self.kwp = KWP2000Client(self.transport)

    def test_diagnostic_session_control_ok(self):
        self.transport.recv = Mock(return_value=b"\x50\x89")
        self.kwp.diagnostic_session_control(SESSION_TYPE.DIAGNOSTIC)
        self.transport.send.assert_called_once_with(b"\x10\x89")

    def test_diagnostic_session_control_security_access(self):
        self.transport.recv = Mock(return_value=b"\x7f\x10\x33")

        with self.assertRaises(NegativeResponseError):
            self.kwp.diagnostic_session_control(SESSION_TYPE.ENGINEERING_MODE)

    def test_request_download_one_byte_resp(self):
        self.transport.recv = Mock(return_value=b"\x74\x10")
        self.assertEqual(self.kwp.request_download(0xA000, 0x10000), 0x10)
        self.transport.send.assert_called_once_with(b"\x34\x00\xa0\x00\x00\x01\x00\x00")

    def test_request_download_two_byte_resp(self):
        self.transport.recv = Mock(return_value=b"\x74\x01\x00")
        self.assertEqual(self.kwp.request_download(0xA000, 0x10000), 0x100)
        self.transport.send.assert_called_once_with(b"\x34\x00\xa0\x00\x00\x01\x00\x00")

    def test_erase_flash(self):
        self.transport.recv = Mock(return_value=b"\x71\xc4")
        self.kwp.erase_flash(0xA000, 0x5FFFF)
        self.transport.send.assert_called_once_with(b"\x31\xc4\x00\xa0\x00\x05\xff\xff")

    def test_calculate_flash_checksum(self):
        self.transport.recv = Mock(return_value=b"\x71\xc5")
        self.kwp.calculate_flash_checksum(0xA000, 0x5FFFF, 0x1234)
        self.transport.send.assert_called_once_with(b"\x31\xc5\x00\xa0\x00\x05\xff\xff\x12\x34")

    def test_transfer_data(self):
        self.transport.recv = Mock(return_value=b"\x76")
        self.kwp.transfer_data(b"\x12\x34\x56\x78")
        self.transport.send.assert_called_once_with(b"\x36\x12\x34\x56\x78")

    def test_request_transfer_exit(self):
        self.transport.recv = Mock(return_value=b"\x77")
        self.kwp.request_transfer_exit()
        self.transport.send.assert_called_once_with(b"\x37")

    def test_request_stop_communication(self):
        self.transport.recv = Mock(return_value=b"\xc2")
        self.kwp.stop_communication()
        self.transport.send.assert_called_once_with(b"\x82")


if __name__ == "__main__":
    unittest.main()
