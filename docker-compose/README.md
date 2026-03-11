# Using docker compose to run a development environment

Using `docker compose` can simplify Dish Manager development in certain cases.

When NOT to use this.
- If you are making any changes to helm charts/any deployment related changes
  - In this case you need to deploy via `helm`  and will have to deploy to minikube.

If you just want to test some changes to the Dish Manager source code that needs the 
Tango environment, then using docker compose can aid in this.

## Deployment

```bash
docker compose   -f tango-db.yml  -f dish-lmc-devices.yaml up
```

This will deploy all the devices, but NOT the DishManager service.
This is so that you can start DishManager on the commandline for ease of development.

The `dish-manager` pod will have your local `src` path mounted in the pod at `/app/src`

### Start DishManager

Connect to the `dish-manager` pod and start the `DishManager` service

```bash
docker exec -it dish-manager  /bin/bash
root@ec80dc9c6d05:/app#
root@ec80dc9c6d05:/app# DishManagerDS SKA001
1|2025-08-01T08:12:10.931Z|INFO|MainThread|set_logging_level|base_device.py#1010|tango-device:mid-dish/dish-manager/SKA001|Logging level set to LoggingLevel.DEBUG on Python and Tango loggers
1|2025-08-01T08:12:10.932Z|INFO|MainThread|update_logging_handlers|logging.py#380|tango-device:mid-dish/dish-manager/SKA001|Logging targets set to ['tango::logger']
1|2025-08-01T08:12:10.937Z|DEBUG|MainThread|_init_logging|base_device.py#418|tango-device:mid-dish/dish-manager/SKA001|Logger initialised
1|2025-08-01T08:12:10.947Z|DEBUG|MainThread|init_device|base_device.py#615|tango-device:mid-dish/dish-manager/SKA001|Groups definitions: None
1|2025-08-01T08:12:10.948Z|DEBUG|MainThread|init_device|base_device.py#619|tango-device:mid-dish/dish-manager/SKA001|No Groups loaded for device: mid-dish/dish-manager/SKA001
...
```

Restart the service when you make code changes.

### Running tests or using itango 

Connect to the `dev-pod` container to run itango or tests

#### itango

```bash
> docker exec -it dev-pod /bin/bash
root@bd44d478b7ce:/app#
root@bd44d478b7ce:/app# pip3 install itango
Collecting itango
  Downloading itango-0.3.0-py3-none-any.whl.metadata (2.7 kB)
Requirement already satisfied: pytango>=9.3.0 in ./.venv/lib/python3.10/site-packages (from itango) (9.5.0)
Collecting ipython<10.0,>=8.5 (from itango)
  Downloading ipython-8.37.0-py3-none-any.whl.metadata (5.1 kB)

  ....

root@bd44d478b7ce:/app# itango
ITango 0.3.0 -- An interactive Tango client.

Running on top of Python 3.10.12, IPython 8.37.0 and PyTango 9.5.0

help      -> ITango's help system.
object?   -> Details about 'object'. ?object also works, ?? prints more.

IPython profile: tango

hint: Try typing: mydev = Device("<tab>

In [1]: dp = DeviceProxy("mid-dish/ds-manager/SKA001")
In [2]: dp.ping()
Out[3]: 384
```

#### Running tests

```bash
> docker exec -it dev-pod  /bin/bash
root@c6ed616e914e:/app# cd tests/
root@c6ed616e914e:/app/tests#
root@c6ed616e914e:/app/tests#
root@c6ed616e914e:/app/tests# pytest  -s ./unit/
============================================================== test session starts ==============================================================
platform linux -- Python 3.10.12, pytest-7.4.4, pluggy-1.6.0
rootdir: /app/tests
plugins: cov-2.12.1, forked-1.6.0, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, repeat-0.9.4, timeout-2.4.0
collected 404 items

unit/business_logic/test_attr_command_logging.py ..
tests/unit/business_logic/test_command_action_handler.py ...
...
```
