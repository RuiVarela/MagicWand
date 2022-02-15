import asyncio
from hardware.command import CommandHardware
from hardware.tuya import TuyaHardware

#
# Run hardware Task
#
async def run(core, current_hardware):
    configuration = core.configuration[current_hardware.device_type()]
    interval = 5
    
    await current_hardware.open(configuration)

    while core.running:
        await asyncio.sleep(interval)
        await current_hardware.step()

    await current_hardware.close()