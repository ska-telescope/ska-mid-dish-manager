Dish Manager
============

[![Documentation Status](https://readthedocs.org/projects/ska-mid-dish-manager/badge/?version=latest)](https://developer.skao.int/projects/ska-mid-dish-manager/en/latest/?badge=latest)


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
$ poetry install
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

## Writing documentation
The documentation for this project, including how to get started with it, can be found in the docs folder.
