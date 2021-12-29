#!/usr/bin/env python3
import struct
from argparse import ArgumentParser

from kwp2000 import ACCESS_TYPE, SESSION_TYPE, KWP2000Client, NegativeResponseError
from panda import Panda
from tp20 import TP20Transport
from tqdm import tqdm


def login(kwp_client, password):
    seed = kwp_client.security_access(ACCESS_TYPE.REQUEST_SEED)
    seed_int = struct.unpack(">I", seed)[0]
    key = struct.pack(">I", seed_int + password)
    kwp_client.security_access(ACCESS_TYPE.SEND_KEY, key)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--known-password", default=40168, help="Kwown password")
    parser.add_argument("--target-mode", default=0x86, help="Target diagnostics mode")
    args = parser.parse_args()

    p = Panda()
    p.can_clear(0xFFFF)
    p.set_safety_mode(Panda.SAFETY_ALLOUTPUT)

    tp20 = TP20Transport(p, 0x9)
    kwp_client = KWP2000Client(tp20)

    for password in tqdm(range(0x10000)):
        # Clear attempts by doing a sucesful login
        try:
            login(kwp_client, args.known_password)
        except NegativeResponseError:
            pass

        # Clear login state by doing a failed mode set
        try:
            kwp_client.diagnostic_session_control(args.target_mode)
        except NegativeResponseError:
            pass

        # Check if password is valid
        try:
            login(kwp_client, password)
            print(f"Valid password {password}")
        except NegativeResponseError:
            pass

        # Try entering target mode
        try:
            kwp_client.diagnostic_session_control(args.target_mode)
            print(f"Valid passowrd {password} for mode {hex(args.target_mode)}")
            kwp_client.diagnostic_session_control(SESSION_TYPE.DIAGNOSTIC)
        except NegativeResponseError:
            pass

        # Keep channel alive
        tp20.can_send(b"\xa3")
        tp20.can_recv()
