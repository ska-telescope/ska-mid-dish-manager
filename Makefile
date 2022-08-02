SHELL=/bin/bash
.SHELLFLAGS=-o pipefail -c

NAME=ska-mid-dish-manager

VERSION=$(shell grep -e "^version = s*" pyproject.toml | cut -d = -f 2 | xargs)
IMAGE=$(CAR_OCI_REGISTRY_HOST)/$(NAME)
DOCKER_BUILD_CONTEXT=.
DOCKER_FILE_PATH=Dockerfile

MINIKUBE ?= true ## Minikube or not
TANGO_HOST ?= tango-databaseds:10000  ## TANGO_HOST connection to the Tango DS

ifeq ($(MAKECMDGOALS),python-test)
MARK = unit
endif

ifeq ($(MAKECMDGOALS),k8s-test)
MARK = acceptance
endif

# Set the specific environment variables required for pytest
PYTHON_VARS_BEFORE_PYTEST ?= PYTHONPATH=.:./src \
							 TANGO_HOST=$(TANGO_HOST)

PYTHON_VARS_AFTER_PYTEST ?= -m '$(MARK)' --forked --json-report --json-report-file=build/report.json --junitxml=build/report.xml --cucumberjson=build/cucumber.json

OCI_TAG = $(VERSION)-dev.c$(CI_COMMIT_SHORT_SHA)

CI_REGISTRY ?= registry.gitlab.com

# Use the previously built image when running in the pipeline
# ifneq ($(CI_JOB_ID),)
# CUSTOM_VALUES = --set dishmanager.image.image=$(NAME) \
# 	--set dishmanager.image.registry=$(CI_REGISTRY)/ska-telescope/$(NAME) \
# 	--set dishmanager.image.tag=$(OCI_TAG)
# K8S_TEST_IMAGE_TO_TEST=$(CI_REGISTRY)/ska-telescope/$(NAME)/$(NAME):$(OCI_TAG)
# endif
K8S_TEST_IMAGE_TO_TEST=registry.gitlab.com/ska-telescope/ska-mid-dish-manager/ska-mid-dish-manager:0.0.1

K8S_CHART_PARAMS = --set global.minikube=$(MINIKUBE) \
	--set global.tango_host=$(TANGO_HOST) \
	$(CUSTOM_VALUES)

# include makefile targets from the submodule
-include .make/k8s.mk
-include .make/helm.mk
-include .make/oci.mk
-include .make/base.mk
-include .make/docs.mk
-include .make/python.mk

# include your own private variables for custom deployment configuration
-include PrivateRules.mak
