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

def has_suffix(payload):
    """Check to see if payload has valid Tuya suffix"""
    if len(payload) < 4:
        return False

    #lg("buffer %r = %r", payload[-4:], SUFFIX_BIN)
    return payload[-4:] == SUFFIX_BIN

def error_json(number=None, payload=None):
    """Return error details in JSON"""
    try:
        spayload = json.dumps(payload)
        # spayload = payload.replace('\"','').replace('\'','')
    except:
        spayload = '""'

    vals = (error_codes[number], str(number), spayload)
    #lg("ERROR %s - %s - payload: %s" % vals)

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
    def __init__(self, logger, payload, minresponse, getresponse, on_con_lost):
        self.logger = logger
        self.payload = payload
        self.minresponse = minresponse
        self.getresponse = getresponse
        self.on_con_lost = on_con_lost
        self.received = None

    def connection_made(self, transport):
        transport.write(self.payload)
        #self.logger(f"Data sent: {self.payload}")

    def data_received(self, data):
        self.received = data
        #self.logger(f"Data Received data={binascii.hexlify(self.received)}")

        # device may send null ack (28 byte) response before a full response
        if len(self.received) <= self.minresponse:
            self.logger(f"received null payload {self.received}, fetch new one")
        else:
            self.on_con_lost.set_result(True)



class BaseDevice:
    def __init__(self, dev_id, address, local_key=""):
        self.logger = defaultLogger
        self.id = dev_id
        self.address = address
        self.local_key = local_key
        self.local_key = local_key.encode("latin1")
        self.connection_timeout = 5
        self.version = 3.3
        self.dev_type = "default"
        self.port = 6668  # default - do not expect caller to pass in
        self.cipher = AESCipher(self.local_key)
        self.dps_to_request = {}
        self.seqno = 0
        self.disabledetect = False


    async def _send_receive(self, payload, minresponse=28, getresponse=True):
        dev_type = self.dev_type
        data = None

        loop = asyncio.get_running_loop()
        on_done = loop.create_future()
        
        factory = lambda: NetworkCommand(self.logger, payload, minresponse, getresponse, on_done)
        transport, protocol = await loop.create_connection(factory, self.address, self.port)
        data = None

        # Wait until the protocol signals that the connection is lost and close the transport.
        try:
            await asyncio.wait_for(on_done, timeout=self.connection_timeout)
            data = protocol.received
        except asyncio.TimeoutError:
            self.logger('Connection timeout!')
        finally:
            transport.close()


         # Unpack Message into TuyaMessage format
        # and return payload decrypted
        try:
            msg = unpack_message(data)
            # Data available: seqno cmd retcode payload crc
            #self.logger(f"raw unpacked message = {msg}")
            result = self._decode_payload(msg.payload)
        except:
            self.logger("error unpacking or decoding tuya JSON payload")
            result = error_json(ERR_PAYLOAD)

        # Did we detect a device22 device? Return ERR_DEVTYPE error.
        if dev_type != self.dev_type:
            self.log.debug("Device22 detected and updated ({dev_type} -> {self.dev_type}) - Update payload and try again")
            result = error_json(ERR_DEVTYPE)

        return result

    def _decode_payload(self, payload):
        cipher = AESCipher(self.local_key)

        if payload.startswith(PROTOCOL_VERSION_BYTES_31):
            # Received an encrypted payload
            # Remove version header
            payload = payload[len(PROTOCOL_VERSION_BYTES_31) :]
            # Decrypt payload
            # Remove 16-bytes of MD5 hexdigest of payload
            payload = cipher.decrypt(payload[16:])
        elif self.version == 3.3:
            # Trim header for non-default device type
            if self.dev_type != "default" or payload.startswith(PROTOCOL_VERSION_BYTES_33):
                payload = payload[len(PROTOCOL_33_HEADER) :]
                self.logger(f"removing 3.3={payload}")
            try:
                #self.logger(f"decrypting={payload}")
                payload = cipher.decrypt(payload, False)
            except:
                self.logger(f"incomplete payload={payload}")
                return None

            #self.logger(f"decrypted 3.3 payload={payload} type {type(payload)}")
            if not isinstance(payload, str):
                try:
                    payload = payload.decode()
                except:
                   self.logger("payload was not string type and decoding failed")
                   return error_json(ERR_JSON, payload)
            if not self.disabledetect and "data unvalid" in payload:
                self.dev_type = "device22"
                # set at least one DPS
                self.dps_to_request = {"1": None}
                self.logger(f"'data unvalid' error detected: switching to dev_type {self.dev_type}")
                return None
        elif not payload.startswith(b"{"):
            self.logger("Unexpected payload=%r", payload)
            return error_json(ERR_PAYLOAD, payload)

        if not isinstance(payload, str):
            payload = payload.decode()
            self.logger(f"decoded results={payload}")
        try:
            json_payload = json.loads(payload)
        except:
            json_payload = error_json(ERR_JSON, payload)
        return json_payload

    def generate_payload(self, command, data=None, gwId=None, devId=None, uid=None):
        """
        Generate the payload to send.
        Args:
            command(str): The type of command.
                This is one of the entries from payload_dict
            data(dict, optional): The data to send.
                This is what will be passed via the 'dps' entry
            gwId(str, optional): Will be used for gwId
            devId(str, optional): Will be used for devId
            uid(str, optional): Will be used for uid
        """
        json_data = payload_dict[self.dev_type][command]["command"]
        command_hb = payload_dict[self.dev_type][command]["hexByte"]

        if "gwId" in json_data:
            if gwId is not None:
                json_data["gwId"] = gwId
            else:
                json_data["gwId"] = self.id
        if "devId" in json_data:
            if devId is not None:
                json_data["devId"] = devId
            else:
                json_data["devId"] = self.id
        if "uid" in json_data:
            if uid is not None:
                json_data["uid"] = uid
            else:
                json_data["uid"] = self.id
        if "t" in json_data:
            json_data["t"] = str(int(time.time()))

        if data is not None:
            if "dpId" in json_data:
                json_data["dpId"] = data
            else:
                json_data["dps"] = data
        if command_hb == "0d":  # CONTROL_NEW
            json_data["dps"] = self.dps_to_request

        # Create byte buffer from hex data
        payload = json.dumps(json_data)
        # if spaces are not removed device does not respond!
        payload = payload.replace(" ", "")
        payload = payload.encode("utf-8")
        #self.logger(f"building payload={payload}")

        if self.version == 3.3:
            # expect to connect and then disconnect to set new
            self.cipher = AESCipher(self.local_key)
            payload = self.cipher.encrypt(payload, False)
            self.cipher = None
            if command_hb != "0a" and command_hb != "12":
                # add the 3.3 header
                payload = PROTOCOL_33_HEADER + payload
        elif command == CONTROL:
            # need to encrypt
            self.cipher = AESCipher(self.local_key)
            payload = self.cipher.encrypt(payload)
            preMd5String = (
                b"data="
                + payload
                + b"||lpv="
                + PROTOCOL_VERSION_BYTES_31
                + b"||"
                + self.local_key
            )
            m = md5()
            m.update(preMd5String)
            hexdigest = m.hexdigest()
            # some tuya libraries strip 8: to :24
            payload = (
                PROTOCOL_VERSION_BYTES_31
                + hexdigest[8:][:16].encode("latin1")
                + payload
            )
            self.cipher = None

        # create Tuya message packet
        msg = TuyaMessage(self.seqno, int(command_hb, 16), 0, payload, 0)
        self.seqno += 1  # increase message sequence number
        buffer = pack_message(msg)
        #self.logger(f"payload generated={binascii.hexlify(buffer)}")
        return buffer

    async def status(self):
        """Return device status."""
        payload = self.generate_payload(DP_QUERY)

        data = await self._send_receive(payload)
        self.logger(f"status() received data={data}")
        # Error handling
        if data and "Err" in data:
            if data["Err"] == str(ERR_DEVTYPE):
                # Device22 detected and change - resend with new payload
                self.logger(f"status() rebuilding payload for device22")
                payload = self.generate_payload(DP_QUERY)
                data = await self._send_receive(payload)

        return data

    async def set_status(self, on, switch=1):
        """
        Set status of the device to 'on' or 'off'.
        Args:
            on(bool):  True for 'on', False for 'off'.
            switch(int): The switch to set
        """
        # open device, send request, then close connection
        if isinstance(switch, int):
            switch = str(switch)  # index and payload is a string
        payload = self.generate_payload(CONTROL, {switch: on})

        data = await self._send_receive(payload)
        self.logger(f"set_status received data=={data}")

        return data

    async def updatedps(self, index=[1]):
        """
        Request device to update index.
        Args:
            index(array): list of dps to update (ex. [4, 5, 6, 18, 19, 20])
        """
        self.logger(f"updatedps() entry (dev_type is {self.dev_type})")
        # open device, send request, then close connection
        payload = self.generate_payload(UPDATEDPS, index)
        data = await self._send_receive(payload, 0)
        self.logger(f"updatedps received data={data}")
        return data

    async def set_value(self, index, value):
        """
        Set int value of any index.
        Args:
            index(int): index to set
            value(int): new value for the index
        """
        # open device, send request, then close connection
        if isinstance(index, int):
            index = str(index)  # index and payload is a string

        payload = self.generate_payload(CONTROL, {index: value})

        data = await self._send_receive(payload)

        return data

    async def turn_on(self, switch=1):
        """Turn the device on"""
        await self.set_status(True, switch)

    async def turn_off(self, switch=1):
        """Turn the device off"""
        await self.set_status(False, switch)



#
# Device Discovery
#
class TuyaDiscovery(asyncio.DatagramProtocol):
    """Datagram handler listening for Tuya broadcast messages."""

    def __init__(self, callback=None):
        """Initialize a new BaseDiscovery."""
        self.devices = {}
        self._listeners = []
        self._callback = callback

        UDP_KEY = md5(b"yGAdlopoPVldABfn").digest()
        self._cipher = AESCipher(UDP_KEY)

    async def start(self, loop):
        """Start discovery by listening to broadcasts."""
        listener = loop.create_datagram_endpoint(
            lambda: self, local_addr=("0.0.0.0", 6666)
        )
        encrypted_listener = loop.create_datagram_endpoint(
            lambda: self, local_addr=("0.0.0.0", 6667)
        )

        self._listeners = await asyncio.gather(listener, encrypted_listener)

    def close(self):
        """Stop discovery."""
        self._callback = None
        for transport, _ in self._listeners:
            transport.close()

    def datagram_received(self, data, addr):
        """Handle received broadcast message."""
        data = data[20:-8]
        try:
            data = self._cipher.decrypt(data, False)
        except Exception:  # pylint: disable=broad-except
            data = data.decode()

        decoded = json.loads(data)
        self.device_found(decoded)

    def device_found(self, device):
        """Discover a new device."""
        if device.get("ip") not in self.devices:
            self.devices[device.get("gwId")] = device

        if self._callback:
            self._callback(device)