
from hardware.base import Hardware
from hardware.tuya_api import TuyaDiscovery
from hardware.tuya_api import BaseDevice

import asyncio

class TuyaLocalHardware(Hardware):
    def __init__(self, core):
        super().__init__(core)
        self.discover = TuyaDiscovery()

    async def start(self, configuration):
        await super().start(configuration)
        await self.discover.start(self.loop)

    async def stop(self):
        await self.discover.stop()
        await super().stop()

    async def step(self):
        await super().step()

        device = BaseDevice("bf77a8fa3ba8440af8kiwx", "192.168.68.30", "7d166a102f0f071c")
        #device = BaseDevice("bfc5f68297929eef7cb863", "192.168.68.27", "1e4b5abdd835c096")
        
        # ceiling lights
        device = BaseDevice("bfaa3aa6bcbda3ed6allx2", "192.168.68.14", "6fbaebfec57c5b8c")

        
        result = await device.status()
        result = await device.turn_off(2)

        await asyncio.sleep(5)
        print("asd")

        # discovered = self.discover.devices
        # for key in discovered:
        #     existing_cfg = [i for i in self.configuration['devices'] if i["id"] == key]
        #     if len(existing_cfg) == 0:
        #         continue

        #     existing_cfg = existing_cfg[0]

        #     element = discovered[key]
        #     existing_matching = [i for i in self.get_devices() if i['cfg']["id"] == key]

        #     if len(existing_matching) == 0:
        #         device = BaseDevice(key, element['ip'], existing_cfg['token'])
        #         result = await device.product()
        #         print("asd") 

        #self.core.log(discovered)