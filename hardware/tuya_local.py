
import datetime
from hardware.base import Hardware
from hardware.tuya_api import TuyaDiscovery
from hardware.tuya_api import Device

import asyncio
import re

class TuyaLocalHardware(Hardware):
    def __init__(self, core):
        super().__init__(core)
        self.discover = TuyaDiscovery()

        self.status_iterator = 0
        self.status_batch = 5

        self.last_refresh = None
        self.refresh_interval = 1.0

    async def start(self, configuration):
        await super().start(configuration)
        await self.discover.start(self.loop)

        if "refresh_batch" in configuration:
            self.status_batch = configuration["refresh_batch"]

        if "refresh_interval" in configuration:
            self.refresh_interval = configuration["refresh_interval"]

        devices = []
        id_counter = 0
        for current in configuration["devices"]:
            type = current["type"]
            device_count = re.findall(r'\.(\d+)$', type)
            device_count = int(device_count[0]) if len(device_count) > 0 else 1
            type = type.rstrip('0123456789.')

            for i in range(device_count):
                id_counter = id_counter + 1
                name = current["name"]
                dp = i + 1

                if device_count > 1:
                    name = f"{name} {dp}"

                device = {
                    'id': self.hardware_type() + "_" + str(id_counter),
                    'name': name,
                    'type': type,
                    'state': 'off',

                    'hardware': Device(current['id'], "", current['token']), 
                    'dp': dp,
                    'cfg': current
                }
                devices.append(device)

        if len(devices) < self.status_batch:
            self.status_batch = len(devices)

        self.devices = devices

    async def stop(self):
        await self.discover.stop()
        await super().stop()

    async def run_action(self, device_id, action):
        device = self.get_device(device_id)
        hardware = device['hardware']

        if hardware.address == "":
            self.core.log(f"Hardware {device_id} not ready for action {action}")
            return False
        
        dp = device["dp"]
        type = device["type"]

        result = None
        if type == "light" or type == "switch":
            if action == "enable":
                result = await device.turn_on(dp)
            else:
                result = await device.turn_off(dp)

        self.core.log(f"Action done: {result}")
        return False    

    def apply_status(self, device, status):
        self.core.log(f"Status {device['name']} : {status}");

    async def step(self):
        await super().step()

        devices = self.get_devices()
        device_count = len(devices)
        if device_count <= 0:
            return 

        # find out the devices ip
        for key in self.discover.devices:
            for device in devices:
                if device['cfg']['id'] != key:
                    continue

                ip = key["ip"]
                if device['hardware'].address != ip:
                    device['hardware'].address = ip
                    self.core.log(f"Updating device {device['name']} with ip {ip}")

        # get the device status
        if self.elapsed(self.last_refresh, self.refresh_interval):

            for i in range(self.status_batch):
                index = (self.status_iterator + i) % device_count
                device = devices[index]
                hardware = device['hardware']
                if hardware.address != "":
                    result = await hardware.status()
                    self.apply_status(device, result)
                    
            self.status_iterator += self.status_batch
            if self.status_iterator > 1000:
                self.status_iterator = 0
            
            self.last_refresh = datetime.datetime.now()



 