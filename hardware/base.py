class Hardware:
    def __init__(self):
        pass

    def device_type(self):
        return type(self).__name__   

    async def open(self, configuration):
        print(f"{type(self).__name__} Opened")
        
    async def step(self):
        print(f"{type(self).__name__} Step")  

    async def close(self):
        print(f"{type(self).__name__} Closed")

      