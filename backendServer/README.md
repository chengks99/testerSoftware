# Backend Server
Code containing below functions:

* establish Redis connection
* establish MQTT connection
* GPIO Plugin Module

### Operation
Run below command to start server:

```python
python3 backend/backend-server.py --redis-host [redis_server_IP] -d
```

At Raspberry Pi, run below command to start adaptor code
```python
python3 adaptor/raspPi.py --redis-host [redis_server_IP] -d
```