# MagicWand
MagicWand is a super lightweight home controller

![MagicWand](https://github.com/RuiVarela/MagicWand/raw/main/readme00.gif)   

It was developed to run on a raspberry pi zero. A zero is more than capable to control your home devices. Homeassistant is an amazing sofware but it is just too heavy.   

It exposes a web app on your lan that acts as a home controller, allowing you to access your devices from anyware on you local network. You are not locked to a single installation of a vendor app.

Supported Hardware
- Tuya devices using cloud api
- Tuya devices using local lan
- Yeelight (like xiaomi bedside lamp 2)
- Android Tvs via adb
- Shell scripts

# Runtime Setup
```
# Create a configuration file base on the provided sample
# you should then setup your handware
cp ./support/configuration_sample.json ./configuration.json
python .\main.py

# install magic wand as a service
sudo cp ~/MagicWand/support/magic_wand /etc/init.d/magic_wand
sudo update-rc.d magic_wand defaults

sudo service magic_wand restart

# check http://magicwand.local:8080/
```

## Configuration Blocks
The best way to understard the configurations blocks is tho check the `support/configuration_sample.json`.   

Base blocks:
- `HttpServer` block configures the web api server. you can currently set the listening port on this block.
- `Groups` Lists the visible groups in the web app. Devices are grouped using the initial text in the name field. A device named `Hall Light` would match an pre existing `Hall` group.
- `Names` renames devices on the ui.
- `DashboardDevices` is a list of devices' names that will also appear in a special group called "Dashboard". "Dashboard" will only appear if it is also listed on the `Groups` block. 

Hardware:
- `DummyHardware` Fake hardware for development purposes. does not actuate on anything. it just show up on screen.
- `CommandHardware` Harware that is controlled via a shellscript. You should place your scripts on the `script` folder. The device name and actual action are passed as arguments to the script. A good reference for this is the provided `sample_device.sh`
- `TuyaCloudHardware` A tuya driver that uses tuya cloud api. Setting up tuya cloud is a pretty messed up process, [this is the sdk reference](https://github.com/tuya/tuya-iot-python-sdk) but basically you need to create a project and link your mobile app to you project. In my case I use the "Smart Life" app. You don't need to create assets and users for assets.
- `TuyaLocalHardware` A tuya driver that uses only your local lan. You'll need to know each device `id` and lan `token`. The driver was based on [tinytuya](https://github.com/jasonacox/tinytuya). (You need local keys found on 'Smart Home Device System > Batch query for the list of associated App user dimension devices')
- `MiioYeelightHardware` Yeelight driver using [python-miio](https://github.com/rytilahti/python-miio) library. This uses only the lan for comunications, you'll need the device lan `token`. this has only been tested on the `xiaomi Bedside lamp 2`
- `AndroidHardware` Android adb driver using [androidtv](https://github.com/JeffLIrion/python-androidtv) library. 
- `MultiDeviceHardware` Virtual Hardware that joins devices of the same kind on a single device. With this you can i.e. group `Living Room Ceiling Light`, and `Living Room Tv Light` on a virtual device `Living Room Light`. and `Living Room Light` turns on or off both his children. 
- `ButtonHardware` Virtual Button that runs a list of device actions when pressed.


## Development Help Commands

```
# Create and select a venv
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Freeze requirements
pip freeze > requirements.txt

# Clean python cache
find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf

# copy folder to pi excluding hidden files
scp -r ./MagicWand/[\!.]* pi@magicwand.local:/home/pi/MagicWand

# show service log
journalctl -u magic_wand

# delete service logs
sudo journalctl --rotate
sudo journalctl --vacuum-time=1s


# allow bind a lowerport like 80 to a user 
sudo setcap 'cap_net_bind_service=+ep' /usr/bin/python3.9
```

## Api calls
- http://localhost:8080/api/maintenance/status
- http://localhost:8080/api/maintenance/shutdown
- http://localhost:8080/api/maintenance/restart
- http://localhost:8080/api/maintenance/log
- http://localhost:8080/api/maintenance/clear_log
- http://localhost:8080/api/device/list
- http://localhost:8080/api/device/CommandHardware_1/enable
- http://localhost:8080/api/device/CommandHardware_1/disable
- http://localhost:8080/api/device/CommandHardware_1/open
- http://localhost:8080/api/device/CommandHardware_1/close
- http://localhost:8080/api/device/CommandHardware_1/stop

