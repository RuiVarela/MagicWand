import asyncio
import traceback
import pathlib
import hardware 
import json
from datetime import datetime
from http_server import HttpServer


class Core:
    def __init__(self):
        self.configuration = None
        self.restart = False
        self.running = True
        self.version = "0.1.1"

        self.groups = []
        self.name_mapper = {}
        self.dashboard_devices = []
        self.hardware = []
        self.http_server = None
        self.log_history_size = 100 * 1024
        self.log_history = []
        
    def log(self, message):
        now = datetime.now()
        timestamp = now.isoformat(sep=' ', timespec='milliseconds')

        message = timestamp + " " + str(message)
        self.log_history.extend(message.splitlines())
        self.log_history = self.log_history[-self.log_history_size:]

        print(message)

    def log_exception(self, tag, exception):
        data = tag + "\n" + "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        self.log(data)

    def _handle_task_result(self, task):
        exception = task.exception()
        if exception:
            self.log_exception('handle_task_result', exception)
            
    def create_task(self, coroutine):
        task = asyncio.create_task(coroutine)
        task.add_done_callback(self._handle_task_result)
        return task

    async def pump(self):
        self.log("Core setting up...")

        configuration_path = pathlib.Path(__file__).parent / 'configuration.json'
        configuration_file = open(configuration_path, "r")
        self.configuration = json.loads(configuration_file.read())
        configuration_file.close()

        if "Groups" in self.configuration:
            self.groups = self.configuration["Groups"]

        if "Names" in self.configuration:
            names = self.configuration["Names"]
            for record in names:
                if "device_name" in record:
                    self.name_mapper[record['device_name']] = record['renamed']

        if "DashboardDevices" in self.configuration:
            self.dashboard_devices = self.configuration["DashboardDevices"]
        
        #
        # Add hardware
        #
        if "DummyHardware" in self.configuration:
            self.hardware.append(hardware.DummyHardware(self))

        if "MultiDeviceHardware" in self.configuration:
            self.hardware.append(hardware.MultiDeviceHardware(self))

        if "ButtonHardware" in self.configuration:
            self.hardware.append(hardware.ButtonHardware(self))

        if "CommandHardware" in self.configuration:        
            self.hardware.append(hardware.CommandHardware(self))
        
        if "TuyaCloudHardware" in self.configuration:
            self.hardware.append(hardware.TuyaCloudHardware(self))

        if "MiioYeelightHardware" in self.configuration:
            self.hardware.append(hardware.MiioYeelightHardware(self))

        all_tasks = []

        self.log("Core starting pump...")
        loop = asyncio.get_event_loop()

        #
        # Web Server
        #
        self.http_server = HttpServer()
        http_server_task = self.create_task(self.http_server.run(self))
        all_tasks.append(http_server_task)

        #
        # run hardware
        #
        hardware_tasks = []
        for current in self.hardware:
            hardware_task = self.create_task(hardware.run(self, current))
            hardware_tasks.append(hardware_task)
            all_tasks.append(hardware_task)

        while self.running:
            # self.log("Core running ok")
            await asyncio.sleep(1)

        self.log("Core Shutting down")

        await asyncio.gather(*all_tasks)
        self.log("Core shutdown completed")

    async def run_device_action(self, device_id, action):
        for current in self.hardware:
            if current.get_device(device_id):
                result = await current.run_action(device_id, action)
                if result:
                    current.complete_action(device_id, action)
                return result
                
        return False

    def get_groups(self):
        return self.groups

    def get_devices(self):
        devices = []
        for current in self.hardware:
            devices.extend(current.get_devices())
        return devices

    def get_device_by_name(self, name):
        devices = [d for d in self.get_devices() if d['name'] == name]
        if len(devices) > 0:
            return devices[0]
        return None


    def _devices_sort_func(self, element):
        return element['group'] + " " + element['type'] + " " + element['name']

    async def get_device_list(self):
        devices = self.get_devices()
        groups = self.get_groups()
        records = []

        for current in devices:       
            group = 'Home'
            name = current["name"]
            on_dashboard = False

            if name in self.dashboard_devices:
                on_dashboard = True

            if name in self.name_mapper:
                name = self.name_mapper[name]

            group_candidates = [current for current in groups if name.startswith(current)]
            if len(group_candidates) > 0:
                group = group_candidates[0]

            element = current.copy()
            if 'cfg' in element:
                element.pop('cfg')

            if 'hardware' in element:
                element.pop('hardware')

            element['name'] = name    
            element['group'] = group
            element['dashboard'] = on_dashboard
            
            records.append(element)

        records.sort(key=self._devices_sort_func)   
        return (groups, records)
