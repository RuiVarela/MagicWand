import asyncio
import concurrent.futures
import subprocess

from hardware.base import Hardware


class CommandHardware(Hardware):
    def __init__(self, core):
        super().__init__(core)
        self.executer = None 

    async def start(self, configuration):
        devices = []
        for current in configuration["devices"]:
            device = {
                'id': self.hardware_type() + "_" + current["id"],
                'name': current["name"],
                'type': current["type"],
                'state': 'off',

                'cfg': current
            }
            devices.append(device)
        self.devices = devices

        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        
        await super().start(configuration)

    async def stop(self):
        self.executor.shutdown()
        self.executor = None

        await super().stop()

    async def run_action(self, device_id, action):
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(self.executor, self._execute_command, device_id, action)
        return (result == 0)

    def _execute_command(self, device_id, action):
        cfg_id = self.get_device(device_id)["cfg"]["id"]
        script = self.get_device(device_id)["cfg"]["script"]

        args = [f"scripts/{script}", cfg_id, action]

        self.core.log("Running command [" + (' | '.join(map(str, args))) + "]")

        try:
            res = subprocess.Popen(args, stdout=subprocess.PIPE)
        except OSError as e:
            self.core.log("Error [" + str(e) + "]")
            return -1

        res.wait() # wait for process to finish; this also sets the returncode variable inside 'res'
        output = res.stdout.read().decode("utf-8")

        self.core.log("Done with output [" + output + "] return code [" + str(res.returncode) + "]")

        return res.returncode
