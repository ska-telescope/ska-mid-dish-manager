Dish Manager
============

[![Documentation Status](https://readthedocs.org/projects/ska-mid-dish-manager/badge/?version=latest)](https://developer.skao.int/projects/ska-mid-dish-manager/en/latest/?badge=latest)


This device provides master control and rolled-up monitoring of dish. When commanded, it propagates the associated command to the relevant sub-elements and updates its related attributes based on the aggregation of progress reported by those sub-elements. It also exposes attributes which directly relate to certain states of the sub-elements without making a proxy to those sub-element devices.

## Requirements

The system used for development needs to have Python 3 and `pip` installed.

## Installation

### From source

- Clone the repo

```bash
git clone git@gitlab.com:ska-telescope/ska-mid-dish-manager.git
```

- Install the package

```bash
 python3 -m pip install .
```

Install the requirements.

```bash
$ pip install poetry
```

## Testing

- Run the tests

```bash
tox
```

- Lint

```bash
tox -e lint
```

## Writing documentation

The documentation generator for this project is not available currently

### Build the documentation
