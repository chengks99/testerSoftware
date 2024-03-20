# Backend Server
Code containing below functions:

* establish Redis connection
* establish MQTT connection
* GPIO Plugin Module

### Operation
At Raspberry Pi, run below command to start controller
```python
python3 raspi/raspi-control.py --redis-host [redis_server_IP] -d
```
