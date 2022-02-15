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

    def get_devices(self):
        return self.devices

    def device_type(self):
        return type(self).__name__   

    async def open(self, configuration):
        self.core.log(f"{type(self).__name__} Opened")
        
    async def step(self):
        #self.core.log(f"{type(self).__name__} Step")  
        pass

    async def close(self):
        self.core.log(f"{type(self).__name__} Closed")

    async def run_action(self, device_id, action):
        #self.core.log(f"{type(self).__name__} run_action device_id={device_id} action={action}")
        return False


      