import os
import pathlib
import datetime

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

        self.refresh_interval = 0.0

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
            self.tvs[mdns] = {
                "mdns": mdns,
                "driver": None,
                "status": None,
                "last_status": None
            } 

            for current in tv["devices"]:
                id_counter = id_counter + 1
                device = {
                    'id': self.hardware_type() + "_" + str(id_counter),
                    'name': current['name'],
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
        action = device["command"]
        driver = tv['driver']

        self.core.log(f"Android [{device['name']}] start {action}")

        if driver == None:
            self.core.log(f"Hardware {device_id} not ready for action {action}")
            return False

        ok = False
        if await driver.adb_connect():
            #driver = AndroidTVAsync(mdns['ip'], adbkey=self.adbkey, signer=self.signer)
            result = await driver.adb_shell("hdmi")

            #result = await driver.turn_off()
            self.core.log(f"Result {result}")  

            await driver.adb_close()
            ok = True

    
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
                    driver.start_intent
                    tv['driver'] = driver
                    self.core.log(f"Creating android device {key}")

            
            if tv['driver'] and self.refresh_interval > 0.0 and self.elapsed(tv['last_status'], self.refresh_interval):
                driver = tv['driver']

                if await driver.adb_connect():
                    #properties = await driver.get_device_properties()
                    #self.core.log(f"properties {properties}")

                    #apps = await driver.get_installed_apps()
                    #self.core.log(f"updated {apps}")

                    state = await tv['driver'].get_properties_dict()
                    tv['state'] = state
                    self.core.log(f"state = {state}")

                    await driver.adb_close()

                tv['last_status'] = datetime.datetime.now()