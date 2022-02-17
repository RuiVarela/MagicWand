import asyncio
import pathlib
import hardware 
import json
from http_server import HttpServer

class Core:
    def __init__(self):
        self.configuration = None
        self.restart = False
        self.running = True
        self.version = "0.1.1"

        self.groups = []
        self.hardware = []
        self.http_server = None
        self.log_history_size = 100
        self.log_history = []
        

    async def setup(self):
        configuration_path = pathlib.Path(__file__).parent / 'configuration.json'
        configuration_file = open(configuration_path, "r")
        self.configuration = json.loads(configuration_file.read())
        configuration_file.close()

        self.groups = self.configuration["Groups"]

        #
        # Add hardware
        #
        self.hardware.append(hardware.CommandHardware(self))
        self.hardware.append(hardware.TuyaHardware(self))

    async def teardown(self):
        pass

    def log(self, message):
        self.log_history.extend(message.splitlines())
        self.log_history = self.log_history[-self.log_history_size:]

        print("> " + message)

    async def pump(self):
        self.log("Core starting pump...")

        all_tasks = []

        #
        # Web Server
        #
        self.http_server = HttpServer()
        http_server_task = asyncio.create_task(self.http_server.run(self))
        all_tasks.append(http_server_task)

        #
        # run hardware
        #
        hardware_tasks = []
        for current in self.hardware:
            hardware_task = asyncio.create_task(hardware.run(self, current))
            hardware_tasks.append(hardware_task)
            all_tasks.append(hardware_task)

        while self.running:
            # self.log("Core running ok")
            await asyncio.sleep(1)

        self.log("Core Shutting down")
        await asyncio.gather(*all_tasks)
        self.log("Core Shutting completed")

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