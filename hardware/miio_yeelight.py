from pytz import NonExistentTimeError
from hardware.base import Hardware
from miio.integrations.yeelight import Yeelight
from miio.miioprotocol import MiIOProtocol
from miio.protocol import Message

import datetime
import logging
import codecs
import logging
import socket
import binascii

class MiioYeelightHardware(Hardware):
    def __init__(self, core):
        super().__init__(core)
        self.discover_count = 0
        self.last_refresh = None
        self.refresh_interval = 5

        self.last_discover = None
        self.discover_interval = 30

    async def start(self, configuration):
        #logging.basicConfig(level=logging.DEBUG)
        devices = []
        counter = 0
        for current in configuration["devices"]:
            counter = counter + 1
            device = {
                'id': self.hardware_type() + "_" + str(counter),
                'name': current["name"],
                'type': "light",
                'state': 'off',

                'cfg': current,
                'hardware': None 
            }
            devices.append(device)
        self.devices = devices
        await super().start(configuration)

    def _sync_discover(self):
        timeout = 1
        addr = "<broadcast>"
        seen_addrs = []
        devices = {}

        # magic, length 32
        helobytes = bytes.fromhex("21310020ffffffffffffffffffffffffffffffffffffffffffffffffffffffff")

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(timeout)
        for _ in range(1):
            s.sendto(helobytes, (addr, 54321))
        while True:
            try:
                data, recv_addr = s.recvfrom(1024)
                m = Message.parse(data)  # type: Message
                #self.core.log(f"Got a response: {m}")

                if recv_addr[0] not in seen_addrs:
                    ip = recv_addr[0]
                    id = binascii.hexlify(m.header.value.device_id).decode()
                    token = codecs.encode(m.checksum, "hex")

                    self.core.log(f"Yeelight IP: {ip} ID: {id} token: {token}")
                    seen_addrs.append(recv_addr[0])

                    devices[id] = ip
            except socket.timeout:
                break
            except Exception as ex:
                self.core.log(f"error while reading discover results: {ex}")
                break
        s.close()

        return devices

    def _sync_refresh(self):
        discovered = {}

        if self.elapsed(self.last_discover, self.discover_interval):
            discovered = self._sync_discover()
            if self.discover_count == 0:
                self.core.log(f"Yeelight Discovered {discovered}")

            self.discover_count = self.discover_count + 1
            self.last_discover = datetime.datetime.now()

        all_discovered = True

        for current in self.devices:
            id = current['cfg']['id']
            token = current['cfg']['token']

            if id in discovered:
                if current['hardware'] != None and discovered[id] != current['hardware'].ip:
                    current['hardware'] = None
                    self.core.log(f"Yeelight {id} ip changed to {discovered[id]}")

                if current['hardware'] == None:
                    current['hardware'] = Yeelight(discovered[id], token)
                    self.core.log(f"Created Yeelight {id}")
    
            if current['hardware'] == None:
                all_discovered = False
                continue

            status = current['hardware'].status()

            value = "on" if status.is_on else "off"
            if current['state'] != value:
                current['state'] = value
                self.core.log("Updated [" +  current['name'] + "] value: " + current['state'])

        
        self.discover_interval = 10 * 60 if all_discovered else 30

            
    async def step(self):
        await super().step()

        if self.elapsed(self.last_refresh, self.refresh_interval):
            await self.loop.run_in_executor(self.executor, self._sync_refresh)
            self.last_refresh = datetime.datetime.now()
            
