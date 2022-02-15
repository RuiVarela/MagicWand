# MagicWand
Control your house with simplicity


# Runtime Setup
Create a configuration file
```
cp configuration_sample.json configuration.json
```


## Development Setup
Create and select a venv
```
python -m venv project_venv

project_venv\Scripts\activate.bat
```

Freeze requirements
```
pip3 freeze > requirements.txt
```

## Api calls
- http://localhost:8080/api/maintenance/status
- http://localhost:8080/api/maintenance/shutdown
- http://localhost:8080/api/maintenance/restart
- http://localhost:8080/api/device/list
- http://localhost:8080/api/device/CommandHardware_1/open
