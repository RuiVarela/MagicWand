from hardware.base import Hardware

class CommandHardware(Hardware):
    def __init__(self):
        super().__init__()

    async def open(self, configuration):
        await super().open(configuration)

