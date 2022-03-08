#
# A Lot of code comes from tinytuya - https://github.com/jasonacox/tinytuya
#
import asyncio
import base64
import struct
import json
import binascii

from Crypto.Cipher import AES 
from collections import namedtuple

# Tuya Command Types
UDP = 0  # HEAT_BEAT_CMD
AP_CONFIG = 1  # PRODUCT_INFO_CMD
ACTIVE = 2  # WORK_MODE_CMD
BIND = 3  # WIFI_STATE_CMD - wifi working status
RENAME_GW = 4  # WIFI_RESET_CMD - reset wifi
RENAME_DEVICE = 5  # WIFI_MODE_CMD - Choose smartconfig/AP mode
UNBIND = 6  # DATA_QUERT_CMD - issue command
CONTROL = 7  # STATE_UPLOAD_CMD
STATUS = 8  # STATE_QUERY_CMD
HEART_BEAT = 9
DP_QUERY = 10  # UPDATE_START_CMD - get data points
QUERY_WIFI = 11  # UPDATE_TRANS_CMD
TOKEN_BIND = 12  # GET_ONLINE_TIME_CMD - system time (GMT)
CONTROL_NEW = 13  # FACTORY_MODE_CMD
ENABLE_WIFI = 14  # WIFI_TEST_CMD
DP_QUERY_NEW = 16
SCENE_EXECUTE = 17
UPDATEDPS = 18  # Request refresh of DPS
UDP_NEW = 19
AP_CONFIG_NEW = 20
GET_LOCAL_TIME_CMD = 28
WEATHER_OPEN_CMD = 32
WEATHER_DATA_CMD = 33
STATE_UPLOAD_SYN_CMD = 34
STATE_UPLOAD_SYN_RECV_CMD = 35
HEAT_BEAT_STOP = 37
STREAM_TRANS_CMD = 38
GET_WIFI_STATUS_CMD = 43
WIFI_CONNECT_TEST_CMD = 44
GET_MAC_CMD = 45
GET_IR_STATUS_CMD = 46
IR_TX_RX_TEST_CMD = 47
LAN_GW_ACTIVE = 240
LAN_SUB_DEV_REQUEST = 241
LAN_DELETE_SUB_DEV = 242
LAN_REPORT_SUB_DEV = 243
LAN_SCENE = 244
LAN_PUBLISH_CLOUD_CONFIG = 245
LAN_PUBLISH_APP_CONFIG = 246
LAN_EXPORT_APP_CONFIG = 247
LAN_PUBLISH_SCENE_PANEL = 248
LAN_REMOVE_GW = 249
LAN_CHECK_GW_UPDATE = 250
LAN_GW_UPDATE = 251
LAN_SET_GW_CHANNEL = 252

# Protocol Versions and Headers
PROTOCOL_VERSION_BYTES_31 = b"3.1"
PROTOCOL_VERSION_BYTES_33 = b"3.3"
PROTOCOL_33_HEADER = PROTOCOL_VERSION_BYTES_33 + 12 * b"\x00"
MESSAGE_HEADER_FMT = ">4I"  # 4*uint32: prefix, seqno, cmd, length
MESSAGE_RECV_HEADER_FMT = ">5I"  # 4*uint32: prefix, seqno, cmd, length, retcode
MESSAGE_END_FMT = ">2I"  # 2*uint32: crc, suffix
PREFIX_VALUE = 0x000055AA
SUFFIX_VALUE = 0x0000AA55
SUFFIX_BIN = b"\x00\x00\xaaU"

# Tuya Packet Format
TuyaMessage = namedtuple("TuyaMessage", "seqno cmd retcode payload crc")

# TinyTuya Error Response Codes
ERR_JSON = 900
ERR_CONNECT = 901
ERR_TIMEOUT = 902
ERR_RANGE = 903
ERR_PAYLOAD = 904
ERR_OFFLINE = 905
ERR_STATE = 906
ERR_FUNCTION = 907
ERR_DEVTYPE = 908
ERR_CLOUDKEY = 909
ERR_CLOUDRESP = 910
ERR_CLOUDTOKEN = 911
ERR_PARAMS = 912
ERR_CLOUD = 913

error_codes = {
    ERR_JSON: "Invalid JSON Response from Device",
    ERR_CONNECT: "Network Error: Unable to Connect",
    ERR_TIMEOUT: "Timeout Waiting for Device",
    ERR_RANGE: "Specified Value Out of Range",
    ERR_PAYLOAD: "Unexpected Payload from Device",
    ERR_OFFLINE: "Network Error: Device Unreachable",
    ERR_STATE: "Device in Unknown State",
    ERR_FUNCTION: "Function Not Supported by Device",
    ERR_DEVTYPE: "Device22 Detected: Retry Command",
    ERR_CLOUDKEY: "Missing Tuya Cloud Key and Secret",
    ERR_CLOUDRESP: "Invalid JSON Response from Cloud",
    ERR_CLOUDTOKEN: "Unable to Get Cloud Token",
    ERR_PARAMS: "Missing Function Parameters",
    ERR_CLOUD: "Error Response from Tuya Cloud",
    None: "Unknown Error",
}


def lg(message):
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


# Misc Helpers
def bin2hex(x, pretty=False):
    if pretty:
        space = " "
    else:
        space = ""

    result = "".join("%02X%s" % (y, space) for y in x)
    return result

def hex2bin(x):
    return bytes.fromhex(x)



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

def has_suffix(payload):
    """Check to see if payload has valid Tuya suffix"""
    if len(payload) < 4:
        return False

    lg("buffer %r = %r", payload[-4:], SUFFIX_BIN)
    return payload[-4:] == SUFFIX_BIN

def error_json(number=None, payload=None):
    """Return error details in JSON"""
    try:
        spayload = json.dumps(payload)
        # spayload = payload.replace('\"','').replace('\'','')
    except:
        spayload = '""'

    vals = (error_codes[number], str(number), spayload)
    lg("ERROR %s - %s - payload: %s" % vals)

    return json.loads('{ "Error":"%s", "Err":"%s", "Payload":%s }' % vals)


# Tuya Device Dictionary - Commands and Payload Template
# See requests.json payload at http s://github.com/codetheweb/tuyapi
# 'default' devices require the 0a command for the DP_QUERY request
# 'device22' devices require the 0d command for the DP_QUERY request and a list of
#            dps used set to Null in the request payload
payload_dict = {
    # Default Device
    "default": {
        AP_CONFIG: {  # [BETA] Set Control Values on Device
            "hexByte": "01",
            "command": {"gwId": "", "devId": "", "uid": "", "t": ""},
        },
        CONTROL: {  # Set Control Values on Device
            "hexByte": "07",
            "command": {"devId": "", "uid": "", "t": ""},
        },
        STATUS: {  # Get Status from Device
            "hexByte": "08",
            "command": {"gwId": "", "devId": ""},
        },
        HEART_BEAT: {"hexByte": "09", "command": {"gwId": "", "devId": ""}},
        DP_QUERY: {  # Get Data Points from Device
            "hexByte": "0a",
            "command": {"gwId": "", "devId": "", "uid": "", "t": ""},
        },
        CONTROL_NEW: {"hexByte": "0d", "command": {"devId": "", "uid": "", "t": ""}},
        DP_QUERY_NEW: {"hexByte": "0f", "command": {"devId": "", "uid": "", "t": ""}},
        UPDATEDPS: {"hexByte": "12", "command": {"dpId": [18, 19, 20]}},
        "prefix": "000055aa00000000000000",
        # Next byte is command "hexByte" + length of remaining payload + command + suffix
        # (unclear if multiple bytes used for length, zero padding implies could be more
        # than one byte)
        "suffix": "000000000000aa55",
    },
    # Special Case Device with 22 character ID - Some of these devices
    # Require the 0d command as the DP_QUERY status request and the list of
    # dps requested payload
    "device22": {
        DP_QUERY: {  # Get Data Points from Device
            "hexByte": "0d",  # Uses CONTROL_NEW command for some reason
            "command": {"devId": "", "uid": "", "t": ""},
        },
        CONTROL: {  # Set Control Values on Device
            "hexByte": "07",
            "command": {"devId": "", "uid": "", "t": ""},
        },
        HEART_BEAT: {"hexByte": "09", "command": {"gwId": "", "devId": ""}},
        UPDATEDPS: {
            "hexByte": "12",
            "command": {"dpId": [18, 19, 20]},
        },
        "prefix": "000055aa00000000000000",
        "suffix": "000000000000aa55",
    },
}



class NetworkCommand(asyncio.Protocol):
    def __init__(self, payload, minresponse, getresponse, on_con_lost):
        self.payload = payload
        self.minresponse = minresponse
        self.getresponse = getresponse
        self.on_con_lost = on_con_lost
        self.received = None

    def connection_made(self, transport):
        transport.write(self.payload)
        lg('Data sent: {!r}'.format(self.payload))

    def data_received(self, data):
        self.received = data
        lg("Data Received data=%r", binascii.hexlify(self.received))

        # device may send null ack (28 byte) response before a full response
        if len(self.received) <= self.minresponse:
            lg("received null payload (%r), fetch new one", self.received)
        else:
            self.on_con_lost.set_result(True)

    def connection_lost(self, exc):
        lg('The server closed the connection')
        self.on_con_lost.set_result(True)


class BaseDevice:
    def __init__(self, dev_id, address, local_key="", dev_type="default"):
        self.id = dev_id
        self.address = address
        self.local_key = local_key
        self.local_key = local_key.encode("latin1")
        self.connection_timeout = 5
        self.version = 3.1
        self.dev_type = dev_type
        self.port = 6668  # default - do not expect caller to pass in
        self.cipher = AESCipher(self.local_key)
        self.dps_to_request = {}
        self.seqno = 0
        self.sendWait = 0.01

    async def _send_receive(self, payload, minresponse=28, getresponse=True):
        success = False
        retries = 0
        dev_type = self.dev_type
        data = None

        loop = asyncio.get_running_loop()
        on_done = loop.create_future()
        
        message = 'Hello World!'
        transport, protocol = await loop.create_connection(lambda: NetworkCommand(message, on_done), self.address, self.port)

        # Wait until the protocol signals that the connection is lost and close the transport.
        try:
            await asyncio.wait_for(on_done, timeout=self.connection_timeout)
        except asyncio.TimeoutError:
            lg('Connection timeout!')
        finally:
            transport.close()