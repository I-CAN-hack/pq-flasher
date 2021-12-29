#!/usr/bin/env python3
import tqdm
from argparse import ArgumentParser

from panda import Panda
from panda.python.ccp import CcpClient, BYTE_ORDER
from tp20 import TP20Transport
from kwp2000 import KWP2000Client, ECU_IDENTIFICATION_TYPE

CHUNK_SIZE = 4

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--start-address", default=0, help="start address")
    parser.add_argument("--end-address", default=0x5FFFF, help="end address (inclusive)")
    parser.add_argument("--output", required=True, help="output file")
    args = parser.parse_args()

    p = Panda()
    p.can_clear(0xFFFF)
    p.set_safety_mode(Panda.SAFETY_ALLOUTPUT)

    print("Connecting using KWP2000...")
    tp20 = TP20Transport(p, 0x9)
    kwp_client = KWP2000Client(tp20)

    print("Reading ecu identification & flash status")
    ident = kwp_client.read_ecu_identifcation(ECU_IDENTIFICATION_TYPE.ECU_IDENT)
    print("ECU identification", ident)

    status = kwp_client.read_ecu_identifcation(ECU_IDENTIFICATION_TYPE.STATUS_FLASH)
    print("Flash status", status)

    print("\nConnecting using CCP...")
    client = CcpClient(p, 1746, 1747, byte_order=BYTE_ORDER.LITTLE_ENDIAN)
    client.connect(0x0)

    progress = tqdm.tqdm(total=args.end_address - args.start_address)

    addr = args.start_address
    client.set_memory_transfer_address(0, 0, addr)

    with open(args.output, "wb") as f:
        while addr < args.end_address:
            f.write(client.upload(CHUNK_SIZE)[:CHUNK_SIZE])
            f.flush()

            addr += CHUNK_SIZE
            progress.update(CHUNK_SIZE)
