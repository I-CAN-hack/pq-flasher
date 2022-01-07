#!/usr/bin/env python3
import time
import tqdm
import sys
import struct
from argparse import ArgumentParser

from panda import Panda  # type: ignore
from tp20 import TP20Transport
from kwp2000 import ACCESS_TYPE, ROUTINE_CONTROL_TYPE, KWP2000Client, SESSION_TYPE, ECU_IDENTIFICATION_TYPE

CHUNK_SIZE = 240


def compute_key(seed):
    key = seed
    for _ in range(3):
        tmp = (key ^ 0x3F_1735) & 0xFFFF_FFFF
        key = (tmp + 0xA3FF_7890) & 0xFFFF_FFFF

        if key < 0xA3FF_7890:
            key = (key >> 1) | (tmp << 0x1F)

        key = key & 0xFFFF_FFFF
    return key


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--input", required=True, help="input to flash")
    parser.add_argument("--start-address", default=0x5E000, type=int, help="start address")
    parser.add_argument("--end-address", default=0x5EFFF, type=int, help="end address (inclusive)")
    args = parser.parse_args()

    with open(args.input, "rb") as input_fw:
        input_fw_s = input_fw.read()

    assert args.start_address < args.end_address
    assert args.end_address < len(input_fw_s)
    assert input_fw_s[-4:] != b"Ende", "Firmware is not patched"

    print("\n[READY TO FLASH]")
    print("WARNING! USE AT YOUR OWN RISK! THIS COULD BREAK YOUR ECU AND REQUIRE REPLACEMENT!")
    print("before proceeding:")
    print("* put vehicle in park, and accessory mode (your engine should not be running)")
    print("* ensure battery is fully charged. A full flash can take up to 15 minutes")
    resp = input("continue [y/n]")
    if resp.lower() != "y":
        sys.exit(1)

    p = Panda()
    p.can_clear(0xFFFF)
    p.set_safety_mode(Panda.SAFETY_ALLOUTPUT)

    print("Connecting...")
    tp20 = TP20Transport(p, 0x9)
    kwp_client = KWP2000Client(tp20)

    print("\nEntering programming mode")
    kwp_client.diagnostic_session_control(SESSION_TYPE.PROGRAMMING)
    print("Done. Waiting to reconnect...")

    for i in range(10):
        time.sleep(1)
        print(f"\nReconnecting... {i}")

        p.can_clear(0xFFFF)
        try:
            tp20 = TP20Transport(p, 0x9)
            break
        except Exception as e:
            print(e)

    kwp_client = KWP2000Client(tp20)

    print("\nReading ecu identification & flash status")
    ident = kwp_client.read_ecu_identifcation(ECU_IDENTIFICATION_TYPE.ECU_IDENT)
    print("ECU identification", ident)

    status = kwp_client.read_ecu_identifcation(ECU_IDENTIFICATION_TYPE.STATUS_FLASH)
    print("Flash status", status)

    print("\nRequest seed")
    seed = kwp_client.security_access(ACCESS_TYPE.PROGRAMMING_REQUEST_SEED)
    print(f"seed: {seed.hex()}")

    seed_int = struct.unpack(">I", seed)[0]
    key_int = compute_key(seed_int)
    key = struct.pack(">I", key_int)
    print(f"key: {key.hex()}")

    print("\n Send key")
    kwp_client.security_access(ACCESS_TYPE.PROGRAMMING_SEND_KEY, key)

    print("\nRequest download")
    size = args.end_address - args.start_address + 1
    chunk_size = kwp_client.request_download(args.start_address, size)
    print(f"Chunk size: {chunk_size}")
    assert chunk_size >= CHUNK_SIZE, "Chosen chunk size too large"

    print("\nErase flash")
    f_routine = kwp_client.erase_flash(args.start_address, args.end_address)
    print("F_routine", f_routine)
    print("Done. Waiting to reconnect...")

    for i in range(10):
        time.sleep(1)
        print(f"\nReconnecting... {i}")

        p.can_clear(0xFFFF)
        try:
            tp20 = TP20Transport(p, 0x9)
            break
        except Exception as e:
            print(e)

    kwp_client = KWP2000Client(tp20)

    print("\nRequest erase results")
    result = kwp_client.request_routine_results_by_local_identifier(ROUTINE_CONTROL_TYPE.ERASE_FLASH)
    assert result == b"\x00", "Erase failed"

    print("\nTransfer data")
    to_flash = input_fw_s[args.start_address : args.end_address + 1]
    checksum = sum(to_flash) & 0xFFFF

    progress = tqdm.tqdm(total=len(to_flash))

    while to_flash:
        chunk = to_flash[:CHUNK_SIZE]
        kwp_client.transfer_data(chunk)

        # Keep channel alive
        tp20.can_send(b"\xa3")
        tp20.can_recv()

        to_flash = to_flash[CHUNK_SIZE:]
        progress.update(CHUNK_SIZE)

    print("\nRequest transfer exit")
    kwp_client.request_transfer_exit()

    print("\nStart checksum check")
    kwp_client.calculate_flash_checksum(args.start_address, args.end_address, checksum)

    print("\nRequest checksum results")
    result = kwp_client.request_routine_results_by_local_identifier(ROUTINE_CONTROL_TYPE.CALCULATE_FLASH_CHECKSUM)
    assert result == b"\x00", "Checksum check failed"

    print("\nStop communication")
    kwp_client.stop_communication()

    print("\nDone!")
