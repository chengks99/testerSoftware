# Tester Software
Contains all software for tester application

## DirectoryTree
|**directories**|**Descriptions**|
|:--:|---|
|**backendServer**|base code backend server which contain Redis & MQTT event bus|
|**documents**|documentation folder|
|**mqttServer**|base code for MQTT server include message extraction and database insertion|
|**TesterDetection**|base code for video tester detection and message exchange|

### Start Redis Server
Please [install Redis](https://redis.io/docs/getting-started/installation/install-redis-on-linux/)

#### For WSL-2
Please follow [redis-server-installation](https://docs.microsoft.com/en-us/windows/wsl/tutorials/wsl-database#install-redis)

```sh
$ sudo service redis-server start
```

### PIP
PIP is package installer for python. It allow user to use for installtion of packages from python package index. To install pip run below command:

```sh
$ sudo apt-get install python3-pip
```

Firstly need to install additional dependencies:

```sh
$ pip3 install -r requirement.txt
```

### Additional Info
Please refer to README for each version of code