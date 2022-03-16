import asyncio
from hardware.base import DummyHardware
from hardware.base import MultiDeviceHardware
from hardware.base import ButtonHardware
from hardware.command import CommandHardware
from hardware.tuya_cloud import TuyaCloudHardware
from hardware.tuya_local import TuyaLocalHardware
from hardware.miio_yeelight import MiioYeelightHardware
from hardware.android import AndroidHardware

#
# Run hardware Task
#
async def run(core, current_hardware):
    configuration = core.configuration[current_hardware.hardware_type()]
    interval = 1
    
    await current_hardware.start(configuration)

    while core.running:
        await asyncio.sleep(interval)
        await current_hardware.step()

    await current_hardware.stop()