#!/usr/bin/env python3
import struct
from argparse import ArgumentParser
import crcmod

# fmt: off

# (addr, orig, new (optional) )
patches = {
    "2501": [
        (0x0005E7A8, b"1K0909144E \x002501", None),  # Software number and version
        (0x0005E221, b"\x64", b"\x00"),  # Disengage countdown
        (0x0005E283, b"\x32", b"\x00"),  # Min speed
        (0x0005FFFC, b"Ende", b"\xff\xff\xff\xff"),  # End of FW marker
    ],
    "3501": [
        (0x0005D828, b"1K0909144R \x003501", None),  # Software number and version
        (0x0005D289, b"\x64", b"\x00"),  # Disengage countdown
        (0x0005D2FA, b"\x14", b"\x00"),  # Min speed
        (0x0005FFFC, b"Ende", b"\xff\xff\xff\xff"),  # End of FW marker
    ]
}

# (checksum addr, start, end)
checksums = {
    "2501": [
        (0x05EFFC, 0x5E000, 0x5EFFC),
    ],
    "3501": [
        #ASW: A000 - 5C000
        (0x05fef8, 0x0a000, 0x0afff),
        (0x05fefa, 0x0afff, 0x0bffe),
        (0x05fefc, 0x0bffe, 0x0cffd),
        (0x05fefe, 0x0cffd, 0x0dffc),
        (0x05ff00, 0x0dffc, 0x0effb),
        (0x05ff02, 0x0effb, 0x0fffa),
        (0x05ff04, 0x0fffa, 0x10ff9),
        (0x05ff06, 0x10ff9, 0x11ff8),
        (0x05ff08, 0x11ff8, 0x12ff7),
        (0x05ff0a, 0x12ff7, 0x13ff6),
        (0x05ff0c, 0x13ff6, 0x14ff5),
        (0x05ff0e, 0x14ff5, 0x15ff4),
        (0x05ff10, 0x15ff4, 0x16ff3),
        (0x05ff12, 0x16ff3, 0x17ff2),
        (0x05ff14, 0x17ff2, 0x18ff1),
        (0x05ff16, 0x18ff1, 0x19ff0),
        (0x05ff18, 0x19ff0, 0x1afef),
        (0x05ff1a, 0x1afef, 0x1bfee),
        (0x05ff1c, 0x1bfee, 0x1cfed),
        (0x05ff1e, 0x1cfed, 0x1dfec),
        (0x05ff20, 0x1dfec, 0x1efeb),
        (0x05ff22, 0x1efeb, 0x1ffea),
        (0x05ff24, 0x1ffea, 0x20fe9),
        (0x05ff26, 0x20fe9, 0x21fe8),
        (0x05ff28, 0x21fe8, 0x22fe7),
        (0x05ff2a, 0x22fe7, 0x23fe6),
        (0x05ff2c, 0x23fe6, 0x24fe5),
        (0x05ff2e, 0x24fe5, 0x25fe4),
        (0x05ff30, 0x25fe4, 0x26fe3),
        (0x05ff32, 0x26fe3, 0x27fe2),
        (0x05ff34, 0x27fe2, 0x28fe1),
        (0x05ff36, 0x28fe1, 0x29fe0),
        (0x05ff38, 0x29fe0, 0x2afdf),
        (0x05ff3a, 0x2afdf, 0x2bfde),
        (0x05ff3c, 0x2bfde, 0x2cfdd),
        (0x05ff3e, 0x2cfdd, 0x2dfdc),
        (0x05ff40, 0x2dfdc, 0x2efdb),
        (0x05ff42, 0x2efdb, 0x2ffda),
        (0x05ff44, 0x2ffda, 0x30fd9),
        (0x05ff46, 0x30fd9, 0x31fd8),
        (0x05ff48, 0x31fd8, 0x32fd7),
        (0x05ff4a, 0x32fd7, 0x33fd6),
        (0x05ff4c, 0x33fd6, 0x34fd5),
        (0x05ff4e, 0x34fd5, 0x35fd4),
        (0x05ff50, 0x35fd4, 0x36fd3),
        (0x05ff52, 0x36fd3, 0x37fd2),
        (0x05ff54, 0x37fd2, 0x38fd1),
        (0x05ff56, 0x38fd1, 0x39fd0),
        (0x05ff58, 0x39fd0, 0x3afcf),
        (0x05ff5a, 0x3afcf, 0x3bfce),
        (0x05ff5c, 0x3bfce, 0x3cfcd),
        (0x05ff5e, 0x3cfcd, 0x3dfcc),
        (0x05ff60, 0x3dfcc, 0x3efcb),
        (0x05ff62, 0x3efcb, 0x3ffca),
        (0x05ff64, 0x3ffca, 0x40fc9),
        (0x05ff66, 0x40fc9, 0x41fc8),
        (0x05ff68, 0x41fc8, 0x42fc7),
        (0x05ff6a, 0x42fc7, 0x43fc6),
        (0x05ff6c, 0x43fc6, 0x44fc5),
        (0x05ff6e, 0x44fc5, 0x45fc4),
        (0x05ff70, 0x45fc4, 0x46fc3),
        (0x05ff72, 0x46fc3, 0x47fc2),
        (0x05ff74, 0x47fc2, 0x48fc1),
        (0x05ff76, 0x48fc1, 0x49fc0),
        (0x05ff78, 0x49fc0, 0x4afbf),
        (0x05ff7a, 0x4afbf, 0x4bfbe),
        (0x05ff7c, 0x4bfbe, 0x4cfbd),
        (0x05ff7e, 0x4cfbd, 0x4dfbc),
        (0x05ff80, 0x4dfbc, 0x4efbb),
        (0x05ff82, 0x4efbb, 0x4ffba),
        (0x05ff84, 0x4ffba, 0x50fb9),
        (0x05ff86, 0x50fb9, 0x51fb8),
        (0x05ff88, 0x51fb8, 0x52fb7),
        (0x05ff8a, 0x52fb7, 0x53fb6),
        (0x05ff8c, 0x53fb6, 0x54fb5),
        (0x05ff8e, 0x54fb5, 0x55fb4),
        (0x05ff90, 0x55fb4, 0x56fb3),
        (0x05ff92, 0x56fb3, 0x57fb2),
        (0x05ff94, 0x57fb2, 0x58fb1),
        (0x05ff96, 0x58fb1, 0x59fb0),
        (0x05ff98, 0x59fb0, 0x5afaf),
        (0x05ff9a, 0x5afaf, 0x5bfae),
        (0x05ff9c, 0x5bfae, 0x5c000),
        #Calibration: 5C000 - 5EFFE
        (0x05DFFC, 0x5C000, 0x5CFFF),
        (0x05DFFE, 0x5CFFF, 0x5DFFC),
        (0x05EFFE, 0x5E000, 0x5EFFE),
    ]
}
# fmt: on


def crc16(dat):
    xmodem_crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0x0000, xorOut=0x0000)
    crc = xmodem_crc_func(dat)
    return struct.pack(">H", crc)


def verify_checksums(fw_in, config):
    for expected, start, end in config:
        if fw_in[expected : expected + 2] != crc16(fw_in[start:end]):
            return False

    return True


def update_checksums(fw_in, config):
    fw_out = fw_in
    for expected, start, end in config:
        fw_out = fw_out[:expected] + crc16(fw_in[start:end]) + fw_out[expected + 2 :]
    return fw_out


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--input", required=True, help="input file to patch")
    parser.add_argument("--output", required=True, help="output file")
    parser.add_argument("--version", default="2501", const="2501", nargs="?", choices=["2501", "3501"])
    args = parser.parse_args()

    with open(args.input, "rb") as input_fw:
        input_fw_s = input_fw.read()

    output_fw_s = input_fw_s

    assert verify_checksums(output_fw_s, checksums[args.version])

    for addr, orig, new in patches[args.version]:
        length = len(orig)
        cur = input_fw_s[addr : addr + length]

        assert cur == orig, f"Unexpected values in input FW {cur.hex()} expected {orig.hex()}"

        if new is not None:
            assert len(new) == length
            output_fw_s = output_fw_s[:addr] + new + output_fw_s[addr + length :]
            assert output_fw_s[addr : addr + length] == new

    output_fw_s = update_checksums(output_fw_s, checksums[args.version])

    assert verify_checksums(output_fw_s, checksums[args.version])
    assert len(output_fw_s) == len(input_fw_s)

    with open(args.output, "wb") as output_fw:
        output_fw.write(output_fw_s)
