# MagicWand
Control your house with simplicity


# Runtime Setup
```
# Create a configuration file base on the provided sample
# you should then setup your handware
cp ./support/configuration_sample.json ./configuration.json

# allow pi user to bind on port 80
sudo setcap CAP_NET_BIND_SERVICE=+eip /usr/bin/python

# install magic wand as a service
sudo cp ~/MagicWand/support/magic_wand /etc/init.d/magic_wand
sudo update-rc.d magic_wand defaults

```
## Development Help Commands

```
# Create and select a venv
python3 -m venv .venv
.venv\Scripts\activate.bat

# Install requirements
pip install -r requirements.txt

# Freeze requirements
pip freeze > requirements.txt

# Clean python cache
find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf

# copy folder to py excluding hidden files
scp -r ./MagicWand/[\!.]* pi@magicwand.local:/home/pi/MagicWand
```

## Api calls
- http://localhost:8080/api/maintenance/status
- http://localhost:8080/api/maintenance/shutdown
- http://localhost:8080/api/maintenance/restart
- http://localhost:8080/api/maintenance/logs
- http://localhost:8080/api/device/list
- http://localhost:8080/api/device/CommandHardware_1/enable
- http://localhost:8080/api/device/CommandHardware_1/disable
- http://localhost:8080/api/device/CommandHardware_1/open
- http://localhost:8080/api/device/CommandHardware_1/close
- http://localhost:8080/api/device/CommandHardware_1/stop

