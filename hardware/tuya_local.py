
from hardware.base import Hardware
from hardware.tuya_local_api import TuyaDiscovery
from hardware.tuya_local_api import Device

import datetime
import asyncio
import re

class TuyaLocalHardware(Hardware):
    def __init__(self, core):
        super().__init__(core)
        self.discover = TuyaDiscovery()

        self.status_iterator = 0
        self.status_batch = 5

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

            base_dp = 1
            if 'dp' in current:
                base_dp = current['dp']

            for i in range(device_count):
                id_counter = id_counter + 1
                name = current["name"]

                dp = base_dp + i
                
                if device_count > 1:
                    name = f"{name} {dp}"

                hardware = Device(current['id'], "", current['token'])
                hardware.logger = self.core.log

                device = {
                    'id': self.hardware_type() + "_" + str(id_counter),
                    'name': name,
                    'type': type,
                    'state': 'off',

                    'last_status': None,
                    'hardware': hardware, 
                    'dp': dp,
                    'cfg': current
                }
                devices.append(device)

        if len(devices) < self.status_batch:
            self.status_batch = len(devices)

        self.devices = devices

    async def stop(self):
        self.discover.close()
        await super().stop()

    async def run_action(self, device_id, action):
        device = self.get_device(device_id)

        self.core.log(f"Tuya [{device['name']}] start {action}")

        hardware = device['hardware']

        if hardware.address == "":
            self.core.log(f"Hardware {device_id} not ready for action {action}")
            return False
        
        dp = device["dp"]
        type = device["type"]
        if type == "curtain":
            if (action == 'enable') or (action == 'open'):
                action = "on"
            elif (action == 'disable') or (action == 'close'):
                action = "off"
        else:
            action = (action == 'enable') or (action == 'open')
        
        result = await hardware.set_status(action, dp)     

        self.core.log(f"Tuya [{device['name']}] end")  

        if result is not None and 'error' not in result:
            return True

        self.core.log(f"Action Error [{device['name']}] {result}")

        return False    

    def apply_status(self, hardware_id, status):
        # self.core.log(f"Status {device['name']} : {status}");
        for device in self.get_devices():
            if device['cfg']['id'] != hardware_id:
                continue
            
            device['last_status'] = datetime.datetime.now()

            dp = str(device["dp"])
            ok = False

            if 'dps' in status and dp in status['dps']:
                value = "on" if status['dps'][dp] else "off"

                if device['type'] == "curtain":
                    value = "off"

                if device['state'] != value:
                    device['state'] = value
                    self.core.log("Tuya [" +  device['name'] + "] value: " + device['state'])

                ok = True

            #self.core.log(f"updated [{device['name']}] status!")

            if not ok:
                self.core.log(f"Failed to apply status [{device['name']}]\n{status}")

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

                ip = self.discover.devices[key]['ip']
                if device['hardware'].address != ip:
                    device['hardware'].address = ip
                    self.core.log(f"Tuya [{device['name']}] ip: {ip}")

        # get the device status
        end = self.status_iterator + self.status_batch
        while self.status_iterator < end:
            index = self.status_iterator % device_count
            device = devices[index]
            self.status_iterator = self.status_iterator + 1

            if self.elapsed(device['last_status'], self.refresh_interval):
                hardware = device['hardware']
                if hardware.address != "" and device['type'] != "curtain":
                    #self.core.log(f"{index} Refreshing device [{device['name']}] status")
                    result = await hardware.status()
                    if 'error' in result:
                        self.core.log(f"Failed to call status [{device['name']}] : {result}")
                    else:
                        self.apply_status(device['cfg']['id'], result)

        if self.status_iterator > 1000:
            self.status_iterator = 0