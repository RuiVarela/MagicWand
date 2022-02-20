import logging
import asyncio
import concurrent.futures

from hardware.base import Hardware
from tuya_iot import (
    TuyaOpenAPI,
    AuthType,
    TuyaOpenMQ,
    TuyaDeviceManager,
    TuyaHomeManager,
    TuyaDeviceListener,
    TuyaDevice,
    TuyaTokenInfo,
    TUYA_LOGGER
)

class TuyaDeviceListener(TuyaDeviceListener):
    def update_device(self, device: TuyaDevice):
        print("_update-->", device)

    def add_device(self, device: TuyaDevice):
        print("_add-->", device)

    def remove_device(self, device_id: str):
        pass

class TuyaHardware(Hardware):
    def __init__(self, core):
        super().__init__(core)
        self.executer = None
        self.openapi = None
        self.openmq = None
        self.deviceManager = None

    def _sync_open(self, configuration):  
        self.openapi = TuyaOpenAPI(configuration['endpoint'], configuration['access_id'], configuration['access_key'])
        self.openapi.connect(configuration['username'], configuration['password'], configuration['country_code'], configuration['schema'])

        self.openmq = TuyaOpenMQ(self.openapi)
        self.openmq.start()

        self.deviceManager = TuyaDeviceManager(self.openapi, self.openmq)
        self.deviceManager.update_device_list_in_smart_home()



    def _sync_close(self):
        self.openmq.stop()

    async def open(self, configuration):
        TUYA_LOGGER.setLevel(logging.DEBUG)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(self.executor, self._sync_open, configuration)
        await super().open(configuration)

        
    async def close(self):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._sync_close)

        self.executor.shutdown()
        await super().close()

    async def step(self):
        await super().step()

