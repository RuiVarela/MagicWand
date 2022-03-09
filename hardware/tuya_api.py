#
# A Lot of code comes from tinytuya - https://github.com/jasonacox/tinytuya
# A lot of code comes from localtuya - https://github.com/rospogrigio/localtuya
#
import asyncio
import base64
import struct
import json
import binascii
import time

from hashlib import md5
from Crypto.Cipher import AES 
from collections import namedtuple

# commands
SET = "set"
STATUS = "status"
HEARTBEAT = "heartbeat"
UPDATEDPS = "updatedps"  # Request refresh of DPS

# DPS that are known to be safe to use with update_dps (0x12) command
UPDATE_DPS_WHITELIST = [18, 19, 20]  # Socket (Wi-Fi)

# This is intended to match requests.json payload at
# https://github.com/codetheweb/tuyapi :
# type_0a devices require the 0a command as the status request
# type_0d devices require the 0d command as the status request, and the list of
# dps used set to null in the request payload (see generate_payload method)

# prefix: # Next byte is command byte ("hexByte") some zero padding, then length
# of remaining payload, i.e. command + suffix (unclear if multiple bytes used for
# length, zero padding implies could be more than one byte)
PAYLOAD_DICT = {
    "type_0a": {
        STATUS: {"hexByte": 0x0A, "command": {"gwId": "", "devId": ""}},
        SET: {"hexByte": 0x07, "command": {"devId": "", "uid": "", "t": ""}},
        HEARTBEAT: {"hexByte": 0x09, "command": {}},
        UPDATEDPS: {"hexByte": 0x12, "command": {"dpId": [18, 19, 20]}},
    },
    "type_0d": {
        STATUS: {"hexByte": 0x0D, "command": {"devId": "", "uid": "", "t": ""}},
        SET: {"hexByte": 0x07, "command": {"devId": "", "uid": "", "t": ""}},
        HEARTBEAT: {"hexByte": 0x09, "command": {}},
        UPDATEDPS: {"hexByte": 0x12, "command": {"dpId": [18, 19, 20]}},
    },
}

# Protocol Versions and Headers
PROTOCOL_VERSION_BYTES_31 = b"3.1"
PROTOCOL_VERSION_BYTES_33 = b"3.3"
PROTOCOL_33_HEADER = PROTOCOL_VERSION_BYTES_33 + 12 * b"\x00"
MESSAGE_HEADER_FMT = ">4I"  # 4*uint32: prefix, seqno, cmd, length
MESSAGE_RECV_HEADER_FMT = ">5I"  # 4*uint32: prefix, seqno, cmd, length, retcode
MESSAGE_END_FMT = ">2I"  # 2*uint32: crc, suffix
PREFIX_VALUE = 0x000055AA
SUFFIX_VALUE = 0x0000AA55

# Tuya Packet Format
TuyaMessage = namedtuple("TuyaMessage", "seqno cmd retcode payload crc")

def defaultLogger(message):
    print(message)

# Cryptography Helpers
class AESCipher(object):
    def __init__(self, key):
        self.bs = 16
        self.key = key

    def encrypt(self, raw, use_base64=True):
        raw = self._pad(raw)
        cipher = AES.new(self.key, mode=AES.MODE_ECB)
        crypted_text = cipher.encrypt(raw)

        if use_base64:
            return base64.b64encode(crypted_text)
        else:
            return crypted_text

    def decrypt(self, enc, use_base64=True):
        if use_base64:
            enc = base64.b64decode(enc)

        cipher = AES.new(self.key, AES.MODE_ECB)
        raw = cipher.decrypt(enc)
        return self._unpad(raw).decode("utf-8")

    def _pad(self, s):
        padnum = self.bs - len(s) % self.bs
        return s + padnum * chr(padnum).encode()

    @staticmethod
    def _unpad(s):
        return s[: -ord(s[len(s) - 1 :])]


def pack_message(msg):
    """Pack a TuyaMessage into bytes."""
    # Create full message excluding CRC and suffix
    buffer = (
        struct.pack(
            MESSAGE_HEADER_FMT,
            PREFIX_VALUE,
            msg.seqno,
            msg.cmd,
            len(msg.payload) + struct.calcsize(MESSAGE_END_FMT),
        )
        + msg.payload
    )
    # Calculate CRC, add it together with suffix
    buffer += struct.pack(
        MESSAGE_END_FMT, binascii.crc32(buffer) & 0xFFFFFFFF, SUFFIX_VALUE
    )
    return buffer

def unpack_message(data):
    """Unpack bytes into a TuyaMessage."""
    header_len = struct.calcsize(MESSAGE_RECV_HEADER_FMT)
    end_len = struct.calcsize(MESSAGE_END_FMT)

    _, seqno, cmd, _, retcode = struct.unpack(
        MESSAGE_RECV_HEADER_FMT, data[:header_len]
    )
    payload = data[header_len:-end_len]
    crc, _ = struct.unpack(MESSAGE_END_FMT, data[-end_len:])
    return TuyaMessage(seqno, cmd, retcode, payload, crc)

def error_json(message, payload=None):
    try:
        spayload = json.dumps(payload)
        # spayload = payload.replace('\"','').replace('\'','')
    except:
        spayload = '""'
    return json.loads('{ "error":"%s", "payload":%s }' % (message, spayload))


class NetworkCommand(asyncio.Protocol):
    def __init__(self, logger, payload, on_con_lost):
        self.logger = logger
        self.payload = payload
        self.on_con_lost = on_con_lost
        self.received = b""
        self.received_payload = None
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        transport.write(self.payload)

    def data_received(self, data):
        self.received += data

        header_len = struct.calcsize(MESSAGE_RECV_HEADER_FMT)
        # Check if enough data for measage header
        if len(self.received) < header_len:
            return

        # Parse header and check if enough data according to length in header
        _, seqno, cmd, length, retcode = struct.unpack_from(MESSAGE_RECV_HEADER_FMT, self.received)
        if len(self.received[header_len - 4 :]) < length:
            return

        # length includes payload length, retcode, crc and suffix
        if (retcode & 0xFFFFFF00) != 0:
            payload_start = header_len - 4
            payload_length = length - struct.calcsize(MESSAGE_END_FMT)
        else:
            payload_start = header_len
            payload_length = length - 4 - struct.calcsize(MESSAGE_END_FMT)

        payload = self.received[payload_start : payload_start + payload_length]

        crc, _ = struct.unpack_from(MESSAGE_END_FMT,
            self.received[payload_start + payload_length : payload_start + length])

        self.received = self.received[header_len - 4 + length :]
        self.received_payload = TuyaMessage(seqno, cmd, retcode, payload, crc)

        try:
            if not self.transport.is_closing():
                self.transport.close()
        except:
            pass

        self.on_con_lost.set_result(True)


class Device:
    def __init__(self, dev_id, address, local_key=""):
        self.logger = defaultLogger
        self.id = dev_id
        self.address = address
        self.local_key = local_key.encode("latin1")
        self.connection_timeout = 1
        self.connection_attempts = 2
        self.version = 3.3
        self.dev_type = "type_0a"
        self.port = 6668  # default - do not expect caller to pass in
        self.cipher = AESCipher(self.local_key)
        self.seqno = 0
        self.dps_to_request = {}

    async def _send_receive(self, payload):
        loop = asyncio.get_running_loop()
        received_payload = None
        transport = None
        
        attempts = self.connection_attempts
        while attempts > 0:
            try:
                on_done = loop.create_future()
                factory = lambda: NetworkCommand(self.logger, payload, on_done) 
                connection_coroutine = loop.create_connection(factory, self.address, self.port)
                transport, protocol = await asyncio.wait_for(connection_coroutine, timeout=self.connection_timeout)

                await asyncio.wait_for(on_done, timeout=self.connection_timeout)
                received_payload = protocol.received_payload.payload
                break
                
            except Exception as e:
                attempts = attempts - 1
            finally:

                try:
                    connection_coroutine.close()
                except:
                    pass
                
                try:
                    if not transport.is_closing():
                        transport.close()
                except:
                    pass
        
        if received_payload is None:
            result = error_json("empty payload")
        else:
            try:
                result = self._decode_payload(received_payload)
            except Exception as e:
                self.logger("error unpacking or decoding tuya JSON payload")
                result = error_json("invalid payload")

        return result

    def _decode_payload(self, payload):
        if not payload:
            payload = "{}"
        elif payload.startswith(b"{"):
            pass
        elif payload.startswith(PROTOCOL_VERSION_BYTES_31):
            payload = payload[len(PROTOCOL_VERSION_BYTES_31) :]  # remove version header
            # remove (what I'm guessing, but not confirmed is) 16-bytes of MD5
            # hexdigest of payload
            payload = self.cipher.decrypt(payload[16:])
        elif self.version == 3.3:
            if self.dev_type != "type_0a" or payload.startswith(PROTOCOL_VERSION_BYTES_33):
                payload = payload[len(PROTOCOL_33_HEADER) :]
            payload = self.cipher.decrypt(payload, False)

            if "data unvalid" in payload:
                self.dev_type = "type_0d"
                self.logger(f"switching to dev_type {self.dev_type}")
                return error_json("dev_type switch", payload)
        else:
            return error_json("unhandled payload", payload)

        if not isinstance(payload, str):
            payload = payload.decode()

        #self.logger(f"Decrypted payload: {payload}")

        return json.loads(payload)

    def generate_payload(self, command, data=None):
        cmd_data = PAYLOAD_DICT[self.dev_type][command]
        json_data = cmd_data["command"]
        command_hb = cmd_data["hexByte"]

        if "gwId" in json_data:
            json_data["gwId"] = self.id
        if "devId" in json_data:
            json_data["devId"] = self.id
        if "uid" in json_data:
            json_data["uid"] = self.id  # still use id, no separate uid
        if "t" in json_data:
            json_data["t"] = str(int(time.time()))

        if data is not None:
            if "dpId" in json_data:
                json_data["dpId"] = data
            else:
                json_data["dps"] = data
        elif command_hb == 0x0D:
            json_data["dps"] = self.dps_to_request

        payload = json.dumps(json_data).replace(" ", "").encode("utf-8")
        #self.logger(f"Send payload: {payload}")

        if self.version == 3.3:
            payload = self.cipher.encrypt(payload, False)
            if command_hb not in [0x0A, 0x12]:
                # add the 3.3 header
                payload = PROTOCOL_33_HEADER + payload
        elif command == SET:
            payload = self.cipher.encrypt(payload)
            to_hash = (
                b"data="
                + payload
                + b"||lpv="
                + PROTOCOL_VERSION_BYTES_31
                + b"||"
                + self.local_key
            )
            hasher = md5()
            hasher.update(to_hash)
            hexdigest = hasher.hexdigest()
            payload = (
                PROTOCOL_VERSION_BYTES_31
                + hexdigest[8:][:16].encode("latin1")
                + payload
            )

        msg = TuyaMessage(self.seqno, command_hb, 0, payload, 0)
        self.seqno += 1
        return pack_message(msg)

    async def status(self):
        payload = self.generate_payload(STATUS)
        return await self._send_receive(payload)

    async def set_status(self, on, switch=1):
        if isinstance(switch, int):
            switch = str(switch)  # index and payload is a string

        payload = self.generate_payload(SET, {switch: on})
        return await self._send_receive(payload)

    async def set_value(self, index, value):
        if isinstance(index, int):
            index = str(index)  # index and payload is a string

        payload = self.generate_payload(SET, {index: value})
        return await self._send_receive(payload)

    async def turn_on(self, switch=1):
        return await self.set_status(True, switch)

    async def turn_off(self, switch=1):
        return await self.set_status(False, switch)

#
# Device Discovery
#
class TuyaDiscovery(asyncio.DatagramProtocol):
    def __init__(self):
        self.devices = {}
        self._listeners = []

        UDP_KEY = md5(b"yGAdlopoPVldABfn").digest()
        self._cipher = AESCipher(UDP_KEY)

    async def start(self, loop):
        listener = loop.create_datagram_endpoint(lambda: self, local_addr=("0.0.0.0", 6666))
        encrypted_listener = loop.create_datagram_endpoint(lambda: self, local_addr=("0.0.0.0", 6667))

        self._listeners = await asyncio.gather(listener, encrypted_listener)

    def close(self):
        self._callback = None
        for transport, _ in self._listeners:
            transport.close()

    def datagram_received(self, data, addr):
        data = data[20:-8]
        try:
            data = self._cipher.decrypt(data, False)
        except Exception:  # pylint: disable=broad-except
            data = data.decode()

        device = json.loads(data)
        self.devices[device.get("gwId")] = device

        