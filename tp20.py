#!/usr/bin/env python3
"""
VW Transport Protoc 2.0 (TP 2.0)
Reference: https://jazdw.net/tp20
"""

import time
import struct
from typing import Optional, List, Tuple

from panda import Panda  # type: ignore


BROADCAST_ADDR = 0x200


class MessageTimeoutError(TimeoutError):
    pass


class TP20Transport:
    def __init__(self, panda: Panda, module: int, bus: int = 0, timeout: float = 0.1, debug: bool = False):
        """Create TP20Transport object and open a channel"""
        self.panda = panda
        self.bus = bus
        self.timeout = timeout
        self.msgs: List[Tuple[int, bytes]] = []

        self.tx_seq = 0
        self.rx_seq = 0
        self.time_between_packets = 0.0

        self.debug = debug
        self.open_channel(module)

    def can_recv(self, addr: Optional[int] = None) -> bytes:
        """Receive messages until a message with the specified address
        is received. Messages on other addresses, or a second message
        with the specified address, will be stored and are returned
        on subsequent calls."""

        if addr is None:
            addr = self.rx_addr

        start_time = time.monotonic()
        while time.monotonic() - start_time < self.timeout:
            while len(self.msgs):
                a, dat = self.msgs.pop(0)
                if a == addr:
                    return dat

            for a, _, dat, bus in self.panda.can_recv():
                if a != addr:
                    continue

                if bus != self.bus:
                    continue

                if self.debug:
                    print(f"RX: {hex(a)} - {dat.hex()}")
                self.msgs.append((a, dat))

        raise MessageTimeoutError("Timed out waiting for message")

    def can_send(self, dat: bytes, addr: Optional[int] = None):
        if addr is None:
            addr = self.tx_addr

        if self.debug:
            print(f"TX: {hex(addr)} - {dat.hex()}")
        self.panda.can_send(addr, dat, self.bus, int(self.timeout * 1000))
        time.sleep(self.time_between_packets)

    def open_channel(self, module: int):
        """Before communicating to an ECU we have to open a channel.
        This is done on the broadcast address of 0x200. We expect a
        reply on 0x200 + module logial address. We ask the destination module
        to broadcast on 0x300. It will reply with an address for us to transmit on."""

        # Dest: <module>
        # Opcode 0xc0 (setup)
        # RX ID: V = 1 (invalid), 0x1000
        # TX ID: 0x300 + V = 0 (valid), 0x0300
        # Application type: 0x01
        self.can_send(bytes([module]) + b"\xc0\x00\x10\x00\x03\x01", BROADCAST_ADDR)

        # Channel setup response (e.g. 00d00003a80701)
        dat = self.can_recv(BROADCAST_ADDR + module)
        if self.debug:
            print(f"Got channel setup response {dat.hex()}")

        status, rx, tx, _ = struct.unpack("<xBHHB", dat)
        if status != 0xD0:
            raise RuntimeError(f"Failed to setup channel, got {dat.hex()}")

        assert rx == 0x300  # We asked for this

        self.rx_addr = rx
        self.tx_addr = tx

        # Set timing parameters
        # Opcode: 0xa0 (Parameters request)
        # Block size: 0x0f
        # T1: 0x8a (time to wait for ack, 10ms * 10 = 100ms)
        # T2: 0xff (always 0xff)
        # T3: 0x0a (interval between packets, 0.1ms * 10 = 1ms)
        # T4: 0xff (always 0xff)
        self.can_send(b"\xa0\x0f\x8a\xff\x0a\xff")

        # Receive timing parameters (e.g. a10f8aff4aff)
        # 0x8a: 10ms * 10 = 100ms
        # 0x4a: 1ms * 10 = 10ms
        dat = self.can_recv()
        if self.debug:
            print(f"Got timing params {dat.hex()}")
        opcode, bs, t1, t4 = struct.unpack("<BBBxBx", dat)
        assert opcode == 0xA1

        # TODO: parse response
        self.time_between_packets = 0.01

        self.tx_seq = 0
        self.rx_seq = 0

    def wait_for_ack(self):
        """Even though both sides have their own sequence counter
        we expect an ack with our own sequence + 1"""
        seq = (self.tx_seq + 1) & 0xF
        if self.can_recv() != bytes([0xB0 | seq]):
            raise RuntimeError("Wrong ack received")

    def send_ack(self):
        """Even though both sides have their own sequence counter
        we send an ack with the counter from the other side + 1"""
        seq = (self.rx_seq + 1) & 0xF
        self.can_send(bytes([0xB0 | seq]))

    def send(self, dat: bytes):
        """Sends longer string of data by dividing into smaller chunks
        and waiting for acknowledge after the last chunk"""
        if len(dat) > 0xFF:
            raise ValueError("Packet longer than 255 bytes not supported")

        # Prepend length
        payload = struct.pack(">H", len(dat)) + dat

        while payload:
            last = len(payload) <= 7  # Wait for ack on last packet

            to_send = bytes([(0x10 if last else 0x20) | self.tx_seq])
            to_send += payload[:7]

            self.can_send(to_send)

            if last:
                self.wait_for_ack()

            self.tx_seq = (self.tx_seq + 1) & 0xF

            payload = payload[7:]

    def recv(self) -> bytes:
        """Receives multiple chunks of a response and combines
        them into a single string"""
        payload = b""
        while True:
            dat = self.can_recv()
            payload += dat[1:]

            typ, seq = dat[0] >> 4, dat[0] & 0xF
            self.rx_seq = seq  # TODO: Check

            if typ == 0x1:  # Last packet, send ack and return data
                self.send_ack()
                break

        length = struct.unpack(">H", payload[:2])[0]
        data = payload[2 : length + 2]
        assert len(data) == length
        return data
