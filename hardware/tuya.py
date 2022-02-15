from hardware.base import Hardware

class TuyaHardware(Hardware):
    def __init__(self, core):
        super().__init__(core)

    async def open(self, configuration):
        await super().open(configuration)
        
    async def close(self):
        await super().close()

    async def step(self):
        await super().step()

