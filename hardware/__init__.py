import asyncio
from hardware.base import DummyHardware
from hardware.base import MultiDeviceHardware
from hardware.base import ButtonHardware
from hardware.command import CommandHardware
from hardware.tuya import TuyaHardware

#
# Run hardware Task
#
async def run(core, current_hardware):
    configuration = core.configuration[current_hardware.hardware_type()]
    interval = 5
    
    await current_hardware.start(configuration)

    while core.running:
        await asyncio.sleep(interval)
        await current_hardware.step()

    await current_hardware.stop()