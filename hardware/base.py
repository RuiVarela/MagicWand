from distutils import core


class Hardware:
    def __init__(self, core):
        self.core = core
        self.devices = []
        pass

    def get_device(self, device_id):
        devices = self.get_devices()
        found = [i for i in devices if i["id"] == device_id]
        if len(found) > 0:
            return found[0]
        return None

    def complete_action(self, device_id, action):
        device = self.get_device(device_id)
        if device['type'] == 'curtain':
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
        self.core.log(f"{type(self).__name__} Started")
        
    async def step(self):
        #self.core.log(f"{type(self).__name__} Step")  
        pass

    async def stop(self):
        self.core.log(f"{type(self).__name__} Stopped")

    async def run_action(self, device_id, action):
        #self.core.log(f"{type(self).__name__} run_action device_id={device_id} action={action}")
        return False

        
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
        
    async def run_action(self, device_id, action):
        self.core.log(f"{type(self).__name__} run_action device_id={device_id} action={action}")
        
        children = self.get_device(device_id)['cfg']['children']
        for current in children:
            device = self.core.get_device_by_name(current)
            if device:
                await self.core.run_device_action(device['id'], action)
            else:
                self.core.log("Unknowns children name: " + current)

        return True