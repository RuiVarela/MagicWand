import datetime
import asyncio
import concurrent.futures

#
# Base Hardware Type
#
class Hardware:
    def __init__(self, core):
        self.core = core
        self.executer = None 
        self.configuration = None
        self.loop = None
        self.devices = []
        pass

    def elapsed(self, ts, seconds):
        if ts == None:
            return True
        delta = round((datetime.datetime.now() - ts).total_seconds())
        return delta > seconds

    def get_device(self, device_id):
        devices = self.get_devices()
        found = [i for i in devices if i["id"] == device_id]
        if len(found) > 0:
            return found[0]
        return None

    def complete_action(self, device_id, action):
        device = self.get_device(device_id)
        if device['type'] == 'curtain' or device['type'] == 'button':
            return

        if action == "enable" or action == "open":
            device['state'] = 'on'
        elif action == "disable" or action == "close":
            device['state'] = 'off'

    def get_devices(self):
        return self.devices

    def hardware_type(self):
        return type(self).__name__   

    async def start(self, configuration):
        self.configuration = configuration

        self.loop = asyncio.get_event_loop()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        self.core.log(f"{type(self).__name__} Started")
        
    async def stop(self):
        self.executor.shutdown()
        self.executor = None
        self.loop = None
        self.core.log(f"{type(self).__name__} Stopped")

        
    async def step(self):
        #self.core.log(f"{type(self).__name__} Step")  
        pass

    async def run_action(self, device_id, action):
        #self.core.log(f"{type(self).__name__} run_action device_id={device_id} action={action}")
        return False

#
# Dummy - a helper device for development
#         
class DummyHardware(Hardware):
    def __init__(self, core):
        super().__init__(core)

    async def start(self, configuration):
        devices = []
        counter = 0
        for current in configuration["devices"]:
            counter = counter + 1

            device = {
                'id': self.hardware_type() + "_" + str(counter),
                'name': current["name"],
                'type': current["type"],
                'state': 'off',

                'cfg': current
            }
            devices.append(device)
        self.devices = devices

        await super().start(configuration)
        
    async def run_action(self, device_id, action):
        self.core.log(f"{type(self).__name__} run_action device_id={device_id} action={action}")
        return True

#
# MultiDevice
# - groups devices of the same kind
# - replays the same command to all children
#
class MultiDeviceHardware(Hardware):
    def __init__(self, core):
        super().__init__(core)

    async def start(self, configuration):
        devices = []
        counter = 0
        for current in configuration["devices"]:
            counter = counter + 1

            if 'children' in current and isinstance(current["children"], list):
                device = {
                    'id': self.hardware_type() + "_" + str(counter),
                    'name': current["name"],
                    'type': current["type"],
                    'state': 'off',

                    'cfg': current
                }
                devices.append(device)
                self.devices = devices
            else:
                self.core.log("invalid children!")


        await super().start(configuration)


    async def step(self):
        for device in self.get_devices():
            state = 'on'
            for current in device['cfg']['children']:
                children_device = self.core.get_device_by_name(current)
                if children_device and children_device['state'] != 'on':
                    state = 'off'
            device['state'] = state

        
    async def run_action(self, device_id, action):
        self.core.log(f"{type(self).__name__} run_action device_id={device_id} action={action}")
        
        children = self.get_device(device_id)['cfg']['children']
        for current in children:
            device = self.core.get_device_by_name(current)
            if device:
                await self.core.run_device_action(device['id'], action)
            else:
                self.core.log("Unknown children name: " + current)

        return True

#
# Button
# a virtual button that runs commands on children devices
#
class ButtonHardware(Hardware):
    def __init__(self, core):
        super().__init__(core)

    async def start(self, configuration):
        devices = []
        counter = 0
        for current in configuration["devices"]:
            counter = counter + 1

            if 'actions' in current and isinstance(current["actions"], list):
                device = {
                    'id': self.hardware_type() + "_" + str(counter),
                    'name': current["name"],
                    'type': 'button',
                    'state': 'off',

                    'cfg': current
                }
                devices.append(device)
                self.devices = devices
            else:
                self.core.log("invalid actions!")


        await super().start(configuration)
        

    async def run_action(self, device_id, action):
        self.core.log(f"{type(self).__name__} run_action device_id={device_id} action={action}")
        
        actions = self.get_device(device_id)['cfg']['actions']
        for current in actions:
            device_name = current['device']
            device_action = current['action']
            device = self.core.get_device_by_name(device_name)
            if device:
                await self.core.run_device_action(device['id'], device_action)
            else:
                self.core.log("Unknown device_name " + device_name + " device_action " + device_action)
        return True