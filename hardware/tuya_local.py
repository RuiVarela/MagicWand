
from hardware.base import Hardware
from hardware.tuya_api import TuyaDiscovery


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

        discovered = self.discover.devices
        for key in discovered:
            element = discovered[key]
            matching = [i for i in self.get_devices() if i['cfg']["id"] == key]


        self.core.log(discovered)