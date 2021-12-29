#!/usr/bin/env python3
import struct
from enum import IntEnum

from panda import Panda  # type: ignore
from tp20 import TP20Transport


class NegativeResponseError(Exception):
    def __init__(self, message, service_id, error_code):
        super().__init__()
        self.message = message
        self.service_id = service_id
        self.error_code = error_code

    def __str__(self):
        return self.message


class InvalidServiceIdError(Exception):
    pass


class InvalidSubFunctionError(Exception):
    pass


class SERVICE_TYPE(IntEnum):
    DIAGNOSTIC_SESSION_CONTROL = 0x10
    ECU_RESET = 0x11
    READ_FREEZE_FRAME_DATA = 0x12
    READ_DIAGNOSTIC_TROUBLE_CODES = 0x13
    CLEAR_DIAGNOSTIC_INFORMATION = 0x14
    READ_STATUS_OF_DIAGNOSTIC_TROUBLE_CODES = 0x17
    READ_DIAGNOSITC_TROUBE_CODES_BY_STATUS = 0x18
    READ_ECU_IDENTIFICATION = 0x1A
    STOP_DIAGNOSTIC_SESSION = 0x20
    READ_DATA_BY_LOCAL_IDENTIFIER = 0x21
    READ_DATA_BY_COMMON_IDENTIFIER = 0x22
    READ_MEMORY_BY_ADDRESS = 0x23
    SET_DATA_RATES = 0x26
    SECURITY_ACCESS = 0x27
    DYNAMICALLY_DEFINE_LOCAL_IDENTIFIER = 0x2C
    WRITE_DATA_BY_COMMON_IDENTIFIER = 0x2E
    INPUT_OUTPUT_CONTROL_BY_COMMON_IDENTIFIER = 0x2F
    INPUT_OUTPUT_CONTROL_BY_LOCAL_IDENTIFIER = 0x30
    START_ROUTINE_BY_LOCAL_IDENTIFIER = 0x31
    STOP_ROUTINE_BY_LOCAL_IDENTIFIER = 0x32
    REQUEST_ROUTINE_RESULTS_BY_LOCAL_IDENTIFIER = 0x33
    REQUEST_DOWNLOAD = 0x34
    REQUEST_UPLOAD = 0x35
    TRANSFER_DATA = 0x36
    REQUEST_TRANSFER_EXIT = 0x37
    START_ROUTINE_BY_ADDRESS = 0x38
    STOP_ROUTINE_BY_ADDRESS = 0x39
    REQUEST_ROUTINE_RESULTS_BY_ADDRESS = 0x3A
    WRITE_DATA_BY_LOCAL_IDENTIFIER = 0x3B
    WRITE_MEMORY_BY_ADDRESS = 0x3D
    TESTER_PRESENT = 0x3E
    ESC_CODE = 0x80
    STOP_COMMUNICATION = 0x82


class ROUTINE_CONTROL_TYPE(IntEnum):
    ERASE_FLASH = 0xC4
    CALCULATE_FLASH_CHECKSUM = 0xC5


class ECU_IDENTIFICATION_TYPE(IntEnum):
    ECU_IDENT = 0x9B
    STATUS_FLASH = 0x9C


class SESSION_TYPE(IntEnum):
    PROGRAMMING = 0x85
    ENGINEERING_MODE = 0x86
    DIAGNOSTIC = 0x89


class ACCESS_TYPE(IntEnum):
    PROGRAMMING_REQUEST_SEED = 1
    PROGRAMMING_SEND_KEY = 2
    REQUEST_SEED = 3
    SEND_KEY = 4


class COMPRESSION_TYPE(IntEnum):
    UNCOMPRESSED = 0x0


class ENCRYPTION_TYPE(IntEnum):
    UNENCRYPTED = 0x0


_negative_response_codes = {
    0x10: "generalReject",
    0x11: "serviceNotSupported",
    0x12: "subFunctionNotSupported-invalidFormat",
    0x21: "busy-RepeatRequest",
    0x22: "conditionsNotCorrect or requestSequenceError",
    0x23: "routineNotComplete",
    0x31: "requestOutOfRange",
    0x33: "securityAccessDenied",
    0x35: "invalidKey",
    0x36: "exceedNumberOfAttempts",
    0x37: "requiredTimeDelayNotExpired",
    0x40: "downloadNotAccepted",
    0x41: "improperDownloadType",
    0x42: "cantDownloadToSpecifiedAddress",
    0x43: "cantDownloadNumberOfBytesRequested",
    0x50: "uploadNotAccepted",
    0x51: "improperUploadType",
    0x52: "cantUploadFromSpecifiedAddress",
    0x53: "cantUploadNumberOfBytesRequested",
    0x71: "transferSuspended",
    0x72: "transferAborted",
    0x74: "illegalAddressInBlockTransfer",
    0x75: "illegalByteCountInBlockTransfer",
    0x76: "illegalBlockTransferType",
    0x77: "blockTransferDataChecksumError",
    0x78: "reqCorrectlyRcvd-RspPending(requestCorrectlyReceived-ResponsePending)",
    0x79: "incorrectByteCountDuringBlockTransfer",
}


class KWP2000Client:
    def __init__(self, transport: TP20Transport, debug: bool = False):
        self.transport = transport
        self.debug = debug

    def _kwp(self, service_type: SERVICE_TYPE, subfunction: int = None, data: bytes = None) -> bytes:
        req = bytes([service_type])

        if subfunction is not None:
            req += bytes([subfunction])
        if data is not None:
            req += data

        if self.debug:
            print(f"KWP TX: {req.hex()}")

        self.transport.send(req)
        resp = self.transport.recv()

        if self.debug:
            print(f"KWP RX: {resp.hex()}")

        resp_sid = resp[0] if len(resp) > 0 else None

        # negative response
        if resp_sid == 0x7F:
            service_id = resp[1] if len(resp) > 1 else -1

            try:
                service_desc = SERVICE_TYPE(service_id).name
            except BaseException:
                service_desc = "NON_STANDARD_SERVICE"

            error_code = resp[2] if len(resp) > 2 else -1

            try:
                error_desc = _negative_response_codes[error_code]
            except BaseException:
                error_desc = resp[3:].hex()

            raise NegativeResponseError("{} - {}".format(service_desc, error_desc), service_id, error_code)

        # positive response
        if service_type + 0x40 != resp_sid:
            resp_sid_hex = hex(resp_sid) if resp_sid is not None else None
            raise InvalidServiceIdError("invalid response service id: {}".format(resp_sid_hex))

        # check subfunction
        if subfunction is not None:
            resp_sfn = resp[1] if len(resp) > 1 else None

            if subfunction != resp_sfn:
                resp_sfn_hex = hex(resp_sfn) if resp_sfn is not None else None
                raise InvalidSubFunctionError(f"invalid response subfunction: {resp_sfn_hex:x}")

        # return data (exclude service id and sub-function id)
        return resp[(1 if subfunction is None else 2) :]

    def diagnostic_session_control(self, session_type: SESSION_TYPE):
        self._kwp(SERVICE_TYPE.DIAGNOSTIC_SESSION_CONTROL, subfunction=session_type)

    def security_access(self, access_type: ACCESS_TYPE, security_key: bytes = b""):
        request_seed = access_type % 2 != 0

        if request_seed and len(security_key) != 0:
            raise ValueError("security_key not allowed")
        if not request_seed and len(security_key) == 0:
            raise ValueError("security_key is missing")

        return self._kwp(SERVICE_TYPE.SECURITY_ACCESS, subfunction=access_type, data=security_key)

    def read_ecu_identifcation(self, data_identifier_type: ECU_IDENTIFICATION_TYPE):
        return self._kwp(SERVICE_TYPE.READ_ECU_IDENTIFICATION, data_identifier_type)

    def request_download(
        self,
        memory_address: int,
        uncompressed_size: int,
        compression_type: COMPRESSION_TYPE = COMPRESSION_TYPE.UNCOMPRESSED,
        encryption_type: ENCRYPTION_TYPE = ENCRYPTION_TYPE.UNENCRYPTED,
    ):
        if memory_address > 0xFFFFFF:
            raise ValueError(f"invalid memory_address {memory_address}")
        if uncompressed_size > 0xFFFFFF:
            raise ValueError(f"invalid uncompressed_size {uncompressed_size}")

        addr = struct.pack(">L", memory_address)[1:]
        size = struct.pack(">L", uncompressed_size)[1:]
        data = addr + bytes([(compression_type << 4) | encryption_type]) + size
        ret = self._kwp(SERVICE_TYPE.REQUEST_DOWNLOAD, subfunction=None, data=data)
        if len(ret) == 1:
            return struct.unpack(">B", ret)[0]
        elif len(ret) == 2:
            return struct.unpack(">H", ret)[0]
        else:
            raise ValueError(f"Invalid response {ret.hex()}")

    def start_routine_by_local_identifier(self, routine_control: ROUTINE_CONTROL_TYPE, data: bytes) -> bytes:
        return self._kwp(SERVICE_TYPE.START_ROUTINE_BY_LOCAL_IDENTIFIER, routine_control, data)

    def request_routine_results_by_local_identifier(self, routine_control: ROUTINE_CONTROL_TYPE) -> bytes:
        return self._kwp(SERVICE_TYPE.REQUEST_ROUTINE_RESULTS_BY_LOCAL_IDENTIFIER, routine_control)

    def erase_flash(self, start_address: int, end_address: int) -> bytes:
        if start_address > 0xFFFFFF:
            raise ValueError(f"invalid start_address {start_address}")
        if end_address > 0xFFFFFF:
            raise ValueError(f"invalid end_address {end_address}")

        start = struct.pack(">L", start_address)[1:]
        end = struct.pack(">L", end_address)[1:]
        return self.start_routine_by_local_identifier(ROUTINE_CONTROL_TYPE.ERASE_FLASH, start + end)

    def calculate_flash_checksum(self, start_address: int, end_address: int, checksum: int) -> bytes:
        if start_address > 0xFFFFFF:
            raise ValueError(f"invalid start_address {start_address}")
        if end_address > 0xFFFFFF:
            raise ValueError(f"invalid end_address {end_address}")
        if checksum > 0xFFFF:
            raise ValueError(f"invalid checksum {checksum}")

        start = struct.pack(">L", start_address)[1:]
        end = struct.pack(">L", end_address)[1:]
        chk = struct.pack(">H", checksum)
        return self.start_routine_by_local_identifier(ROUTINE_CONTROL_TYPE.CALCULATE_FLASH_CHECKSUM, start + end + chk)

    def transfer_data(self, data: bytes) -> bytes:
        return self._kwp(SERVICE_TYPE.TRANSFER_DATA, data=data)

    def request_transfer_exit(self) -> bytes:
        return self._kwp(SERVICE_TYPE.REQUEST_TRANSFER_EXIT)

    def stop_communication(self) -> bytes:
        return self._kwp(SERVICE_TYPE.STOP_COMMUNICATION)


if __name__ == "__main__":
    p = Panda()
    p.can_clear(0xFFFF)
    p.set_safety_mode(Panda.SAFETY_ALLOUTPUT)

    tp20 = TP20Transport(p, 0x9, debug=False)
    kwp_client = KWP2000Client(tp20, debug=True)
    kwp_client.diagnostic_session_control(SESSION_TYPE.DIAGNOSTIC)

    ident = kwp_client.read_ecu_identifcation(ECU_IDENTIFICATION_TYPE.ECU_IDENT)
    print(f"Part Number {ident[:10]}")

    status = kwp_client.read_ecu_identifcation(ECU_IDENTIFICATION_TYPE.STATUS_FLASH)
    print("Flash status", status)
