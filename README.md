Dish Manager
============

[![Documentation Status](https://readthedocs.org/projects/ska-telescope-ska-mid-dish-manager/badge/?version=latest)](https://developer.skao.int/projects/ska-mid-dish-manager/en/latest/?badge=latest)

This device provides master control and rolled-up monitoring of dish. When commanded, it propagates the associated command to the relevant subservient devices and updates its related attributes based on the aggregation of progress reported by those devices.

## Requirements

The system used for development needs to have Python 3 and `pip` installed.

## Installation

### From source

- Clone the repo

```bash
git clone git@gitlab.com:ska-telescope/ska-mid-dish-manager.git
```

- Install poetry

```bash
pip install poetry
```

Install the dependencies and the package.

```bash
poetry install
```

## Testing

- Run the tests

```bash
make python-test
```

- Lint

```bash
make python-lint
```

## Development

### Deploy the chart with simulators

- Deploy the chart with simulator devices

```
helm upgrade --install dev . -n dish-manager --set global.minikube=true --set ska-mid-dish-simulators.enabled=true --set deviceServers.dsdevice.enabled=true --set ska-mid-dish-simulators.deviceServers.spfdevice.enabled=true --set ska-mid-dish-simulators.deviceServers.spfrxdevice.enabled=true
```

### Deploy for development

- Deploy the chart, but replace the dishmanager pod with a development pod for testing DishManager

```
helm upgrade --install dev . -n dish-manager --set global.minikube=true --set ska-mid-dish-simulators.enabled=true --set deviceServers.dsdevice.enabled=true --set ska-mid-dish-simulators.deviceServers.spfdevice.enabled=true --set ska-mid-dish-simulators.deviceServers.spfrxdevice.enabled=true --set="dev_pod.enabled=true" --set "deviceServers.dishmanager.enabled=false"
```

- Then start DishManager in the commandline

```
/usr/bin/python3 /app/src/ska_mid_dish_manager/devices/DishManagerDS.py 01
```

## Writing documentation

The documentation for this project, including how to get started with it, can be found in the docs folder.
