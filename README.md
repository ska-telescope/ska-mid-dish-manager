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
git clone --recursive git@gitlab.com:ska-telescope/ska-mid-dish-manager.git
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

### If ska-tango-operator has not been installed, install it as below

- Deploy the ska-tango-operator to manage pods and their configurations.

```bash
$ helm repo add k8s-helm-repository https://artefact.skao.int/repository/helm-internal
$ kubectl create namespace ska-tango-operator-system
$ helm upgrade --install to k8s-helm-repository/ska-tango-operator -n ska-tango-operator-system
```

### Deploy the chart with simulators

- Deploy the chart with simulator devices
  
```bash
kubectl create namespace dish-manager
```

```bash
$ helm upgrade --install dev charts/ska-mid-dish-manager -n dish-manager \
--set global.minikube=true \
--set global.operator=true \
--set global.dishes="{001,002}" \ # number of instances to deploy; if not specified defaults to 001
--set ska-mid-dish-simulators.enabled=true \
--set ska-mid-dish-simulators.dsOpcuaSimulator.enabled=true \
--set ska-mid-dish-simulators.deviceServers.spfdevice.enabled=true \
--set ska-mid-dish-simulators.deviceServers.spfrxdevice.enabled=true \
--set ska-mid-dish-ds-manager.enabled=true
--set ska-mid-wms.enabled=true \
--set ska-mid-wms.deviceServers.wms0.enabled=true \
--set ska-mid-wms.simulator.weatherStations="{"0"}"
```

`ska-tango-base` is not deployed by default, to deploy it add the `--set` below:

```bash
--set ska-tango-base.enabled=true
```

### Deploy for development

- Deploy the chart, but replace the dishmanager pod with a development pod for testing DishManager

```bash
$ helm upgrade --install dev charts/ska-mid-dish-manager -n dish-manager \
--set global.minikube=true \
--set global.operator=true \
--set global.dishes={001,002} \ # number of instances to deploy; if not specified defaults to 001
--set dev_pod.enabled=true \ # enable devpod for development
--set deviceServers.dishmanager.enabled=false \ # disable dishmanager to use devpod
--set ska-mid-dish-simulators.enabled=true \
--set ska-mid-dish-simulators.dsOpcuaSimulator.enabled=true \
--set ska-mid-dish-simulators.deviceServers.spfdevice.enabled=true \
--set ska-mid-dish-simulators.deviceServers.spfrxdevice.enabled=true \
--set ska-mid-dish-ds-manager.enabled=true
--set ska-mid-wms.enabled=true \
--set ska-mid-wms.deviceServers.wms0.enabled=true \
--set ska-mid-wms.simulator.weatherStations="{"0"}"
```

- Then start DishManager in the commandline

```
/usr/bin/python3 /app/src/ska_mid_dish_manager/devices/DishManagerDS.py 01
```
For dish mananager example usage, consult the [user guide](https://developer.skao.int/projects/ska-mid-dish-manager/en/latest/user_guide/index.html) in the docs.

## Writing documentation

The documentation for this project can be found in the docs folder. To generate the docs locally,
run the command below and browse the docs from `docs/build/html/index.html`.

```bash
make docs-build html
```

Use the code below to generate the mode transition graph:

```python
from ska_mid_dish_manager.models.dish_mode_model import DishModeModel
from  matplotlib import pyplot as plt
import networkx as nx

model = DishModeModel()
# create a matplotlib axis object
ax = plt.subplot(121)

# draw the transitions
nx.draw(model.dishmode_graph, ax=axis, with_labels=True, font_weight='bold')
plt.show()
```
