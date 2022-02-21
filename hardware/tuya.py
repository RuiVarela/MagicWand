import datetime
import logging
import asyncio
import concurrent.futures

from hardware.base import Hardware
from tuya_iot import (
    TuyaOpenAPI,
    TuyaOpenMQ,
    TuyaDeviceManager,
    TUYA_LOGGER
)

class LogHandler(logging.StreamHandler):
    def __init__(self, core):
        super().__init__(self)
        self.core = core

    def emit(self, record):
        msg = self.format(record)
        self.core.log(msg)

class TuyaHardware(Hardware):
    def __init__(self, core):
        super().__init__(core)
        self.executer = None
        self.openapi = None
        self.openmq = None
        self.deviceManager = None
        self.lastUpdate = datetime.datetime.now()
        self.updateInterval = 5 * 60
        self.loop = asyncio.get_event_loop()

    def _sync_device_map(self):
        for tuyaId in self.deviceManager.device_map.keys():
            tuyaDevice = self.deviceManager.device_map.get(tuyaId)

            for status in tuyaDevice.status.keys():
                type = None
                if status == "switch_1" or status == "switch_2":
                    type = "switch"
                elif status == "switch_led":
                    type = "light"
                #else:
                #    self.core.log("Unknown status: " + status);
                
                if type is None:
                    continue


                id = self.hardware_type() + "|" + tuyaId + "|" + status
                device = self.get_device(id)
                if device is None:
                    device = {
                        'id': id,
                        'type': type,
                        'state': 'off'
                    }
                    self.devices.append(device)
                
                # update data
                device['name'] = tuyaDevice.name
                if tuyaDevice.product_name.startswith('2G'):
                    device['name'] += " " + status[-1]

                value = "on" if str(tuyaDevice.status[status]) == "True" else "off"
                if device['state'] != value:
                    device['state'] = value
                    self.core.log("Updated [" +  device['name'] + "] value: " + device['state'])

   

            #status.switch_1
            #

    def _sync_refresh(self): 
        ids = []
        for device_id in self.deviceManager.device_map.keys():
            ids.append(device_id)

        if len(ids) == 0:
            self.deviceManager.update_device_list_in_smart_home()
        else:
            self.deviceManager._update_device_list_status_cache(ids)

        self._sync_device_map()
        self.lastUpdate = datetime.datetime.now()

    def _sync_open(self, configuration):  
        self.openapi = TuyaOpenAPI(configuration['endpoint'], configuration['access_id'], configuration['access_key'])
        self.openapi.set_dev_channel("hass")
        self.openapi.connect(configuration['username'], configuration['password'], configuration['country_code'], configuration['schema'])

        self.openmq = TuyaOpenMQ(self.openapi)
        self.openmq.start()

        self.deviceManager = TuyaDeviceManager(self.openapi, self.openmq)
        self._sync_refresh()

    def _sync_close(self):
        self.openmq.stop()
        self.openapi = None
        self.openmq = None
        self.deviceManager = None

    async def open(self, configuration):
        # TUYA_LOGGER.setLevel(logging.DEBUG)
        TUYA_LOGGER.setLevel(logging.INFO)
        TUYA_LOGGER.addHandler(LogHandler(self.core))
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        await self.loop.run_in_executor(self.executor, self._sync_open, configuration)
        await super().open(configuration)

    async def run_action(self, device_id, action):
        await super().run_action(device_id, action)
        self.core.log(f"{type(self).__name__} run_action device_id={device_id} action={action}")
        return True
        
    async def close(self):
        await self.loop.run_in_executor(self.executor, self._sync_close)
        self.executor.shutdown()
        await super().close()

    async def step(self):
        await super().step()
        delta = round((datetime.datetime.now() - self.lastUpdate).total_seconds())

        if delta > self.updateInterval:
            await self.loop.run_in_executor(self.executor, self._sync_refresh)
        

