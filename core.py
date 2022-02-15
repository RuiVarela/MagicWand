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

        self.hardware = []
        self.http_server = None

    async def setup(self):
        configuration_path = pathlib.Path(__file__).parent / 'configuration.json'
        configuration_file = open(configuration_path, "r")
        self.configuration = json.loads(configuration_file.read())
        configuration_file.close()

        #
        # Add hardware
        #
        self.hardware.append(hardware.CommandHardware())
        self.hardware.append(hardware.TuyaHardware())


    async def teardown(self):
        pass

    async def pump(self):
        print("Core starting pump...")

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
            # print("Core running ok")
            await asyncio.sleep(1)

        print("Core Shutting down")
        await asyncio.gather(*all_tasks)
        print("Core Shutting completed")
