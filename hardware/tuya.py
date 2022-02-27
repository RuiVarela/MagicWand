import datetime
import logging
import asyncio
import concurrent.futures
import traceback

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
        self.configuration = None
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
                elif status == "control" and tuyaDevice.product_name == 'Curtain switch':
                    type = "curtain"
                #else:
                #    self.core.log(tuyaDevice.product_name + " > Unknown status: " + status);
                
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

    def _sync_refresh(self): 
        try:

            if self.openapi == None:
                self._sync_open()

            if self.openapi == None:
                return

            ids = []
            for device_id in self.deviceManager.device_map.keys():
                ids.append(device_id)

            if len(ids) == 0:
                self.deviceManager.update_device_list_in_smart_home()
            else:
                self.deviceManager._update_device_list_status_cache(ids)
                
        except Exception as exception:
            self.core.log_exception('_sync_refresh', exception)

        self._sync_device_map()
        self.lastUpdate = datetime.datetime.now()

    def _sync_open(self): 
        self.core.log("Tuya trying to connect...")
        self._sync_close()

        configuration = self.configuration

        self.openapi = TuyaOpenAPI(configuration['endpoint'], configuration['access_id'], configuration['access_key'])
        self.openapi.set_dev_channel("hass")
        self.openapi.connect(configuration['username'], configuration['password'], configuration['country_code'], configuration['schema'])

        if self.openapi.is_connect():
            self.openmq = TuyaOpenMQ(self.openapi)
            self.openmq.start()

            self.deviceManager = TuyaDeviceManager(self.openapi, self.openmq)
            self.core.log("Tuya connected")
        else:
            self.core.log("Tuya failed to connect")
            self._sync_close()


    def _sync_close(self):
        if self.openmq:
            self.openmq.stop()
            self.openmq = None

        self.openapi = None
        self.deviceManager = None

    def _sync_update_status(self, device, device_id, status, value):
        self.core.log(f"{type(self).__name__} run_action device_id={device_id} status={status} value={value}")

        if device is None:
            self.core.log("Empty device")
            return 0

        if device['type'] != 'curtain':
            value = (value == 'enable') or (value == 'open')

        commands = [{'code': status, 'value': value}]
        
        try:

            if self.deviceManager:
                response = self.deviceManager.send_commands(device_id, commands)
                if response["success"]:
                    return True
                else:
                    self.core.log(response)

        except Exception as exception:
            self.core.log_exception('_sync_update_status', exception)
            
        return False

    async def start(self, configuration):
        self.configuration = configuration

        # TUYA_LOGGER.setLevel(logging.DEBUG)
        TUYA_LOGGER.setLevel(logging.INFO)
        TUYA_LOGGER.addHandler(LogHandler(self.core))
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        await self.loop.run_in_executor(self.executor, self._sync_refresh)
        await super().start(configuration)
        
    async def stop(self):
        await self.loop.run_in_executor(self.executor, self._sync_close)
        self.executor.shutdown()
        await super().stop()

    async def step(self):
        await super().step()
        delta = round((datetime.datetime.now() - self.lastUpdate).total_seconds())

        if delta > self.updateInterval:
            await self.loop.run_in_executor(self.executor, self._sync_refresh)

    async def run_action(self, device_id, action):
        # self.core.log(f"{type(self).__name__} run_action device_id={device_id} action={action}")
        device_id_parts = device_id.split('|')
        device = self.get_device(device_id)
        return await self.loop.run_in_executor(self.executor, self._sync_update_status, device, device_id_parts[1], device_id_parts[2], action)

        

