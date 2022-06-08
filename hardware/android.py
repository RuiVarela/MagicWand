import asyncio
import os
import pathlib
import datetime
from telnetlib import AYT

from adb_shell.auth.keygen import keygen
from androidtv.adb_manager.adb_manager_async import ADBPythonAsync
from androidtv.androidtv.androidtv_async import AndroidTVAsync

from hardware.base import Hardware

class AndroidHardware(Hardware):
    def __init__(self, core):
        super().__init__(core)
        self.tvs = {}
        self.signer = None
        self.adbkey = None

        self.refresh_interval = 30.0

    async def start(self, configuration):
        #
        # ensure an adb key
        #
        self.adbkey  = str(pathlib.Path(__file__).parent.parent / 'android.adbkey')
        if not os.path.isfile(self.adbkey ):
            # Generate ADB key files
            keygen(self.adbkey )

        # Load the ADB key
        self.signer = await ADBPythonAsync.load_adbkey(self.adbkey)
        self.core.log(f"using Python ADB implementation with adbkey='{self.adbkey}'")


        #
        # Setup tvs
        #
        devices = []
        id_counter = 0
        for tv in configuration["tvs"]:
            mdns = tv['mdns']

            id_counter = id_counter + 1
            device = {
                'id': self.hardware_type() + "_" + str(id_counter),
                'name': tv['name'],
                'type': 'switch',
                'state': 'off',
                
                "driver": None,
                "status": None,
                "last_status": None,

                "mdns": mdns
            }
            self.tvs[mdns] = device
            devices.append(device)

            buttons = []
            if "buttons" in tv:
                buttons.extend(tv["buttons"])

            if "buttons" in configuration:
                buttons.extend(configuration["buttons"])

            for current in buttons:
                id_counter = id_counter + 1
                device = {
                    'id': self.hardware_type() + "_" + str(id_counter),
                    'name': tv['name'] + " " + current['name'],
                    'type': 'button',
                    'state': 'off',

                    "mdns": mdns,
                    "command": current["command"],
                }
                devices.append(device)

        self.devices = devices
        await super().start(configuration)


    async def run_action(self, device_id, action):
        device = self.get_device(device_id)
        tv = self.tvs[device["mdns"]]

        if "command" in device:
            action = device["command"]

        driver = tv['driver']
        self.core.log(f"Android [{device['name']}] start {action}")

        if driver == None:
            self.core.log(f"Hardware {device_id} not ready for action {action}")
            return False

        ok = False

        try:
            if await driver.adb_connect():
                if action == "turn_off" or action == "disable":
                    result = await driver.turn_off()
                elif action == "turn_on" or action == "enable":
                    result = await driver.turn_on()
                else:
                    result = await driver.adb_shell(action)
                #self.core.log(f"Result {result}")  
                await driver.adb_close()
                ok = True
            else:
                self.core.log(f"Android [{device['name']}] unable to establish a connection") 
                tv['driver'] = None

        except Exception as exception:
            self.core.log_exception(f"Failed", exception)

        self.core.log(f"Android [{device['name']}] end")  
        return ok    

    async def step(self):
        await super().step()

        for key, tv in self.tvs.items():
            mdns = self.core.get_mdns(key)
            
            if mdns:
                if tv['driver'] and tv['driver'].host != mdns['ip']:
                    self.core.log(f"Android device {key} changed ip")
                    tv['driver'] = None

                if tv['driver'] == None:
                    driver = AndroidTVAsync(mdns['ip'], adbkey=self.adbkey, signer=self.signer)
                    tv['driver'] = driver
                    self.core.log(f"Creating android device {key}")

            
            if tv['driver'] and self.refresh_interval > 0.0 and self.elapsed(tv['last_status'], self.refresh_interval):
                driver = tv['driver']
                try:
                    if await driver.adb_connect():
                        status = await tv['driver'].get_properties_dict()
                        tv['status'] = status
                        tv['state'] = 'on' if status['screen_on'] else 'off'
                        #self.core.log(f"state = {state}")
                        await driver.adb_close()
                    else:
                        self.core.log(f"Android [{tv['name']}] unable to establish a connection") 
                        tv['driver'] = None
                except Exception as exception:
                    self.core.log(f"Failed to update {tv['name']}")
                    #self.core.log_exception(f"Failed", exception)
                    
                tv['last_status'] = datetime.datetime.now()