#############################
# BASE
#############################
SHELL=/bin/bash
.SHELLFLAGS=-o pipefail -c

NAME=ska-mid-dish-manager
VERSION=$(shell grep -e "^version = s*" pyproject.toml | cut -d = -f 2 | xargs)
IMAGE=$(CAR_OCI_REGISTRY_HOST)/$(NAME)
DOCKER_BUILD_CONTEXT=.
DOCKER_FILE_PATH=Dockerfile

MINIKUBE ?= true ## Minikube or not
SKA_TANGO_OPERATOR = true
TANGO_HOST ?= tango-databaseds:10000  ## TANGO_HOST connection to the Tango DS
CLUSTER_DOMAIN ?= cluster.local## Domain used for naming Tango Device Servers

-include .make/base.mk


#############################
# DOCS
#############################
-include .make/docs.mk


#############################
# PYTHON
#############################
# Set the specific environment variables required for pytest
PYTHON_SWITCHES_FOR_BLACK ?= --line-length 99
PYTHON_SWITCHES_FOR_ISORT ?= -w 99
PYTHON_SWITCHES_FOR_FLAKE8 ?= --max-line-length=99
PYTHON_LINE_LENGTH ?= 99

PYTHON_VARS_BEFORE_PYTEST ?= PYTHONPATH=.:./src \
							 TANGO_HOST=$(TANGO_HOST)
PYTHON_VARS_AFTER_PYTEST ?= -m '$(MARK)' --forked --json-report --json-report-file=build/report.json --junitxml=build/report.xml --cucumberjson=build/cucumber.json --event-storage-files-path="build/events"

python-test: MARK = unit
k8s-test-runner: MARK = acceptance
k8s-test-runner: TANGO_HOST = tango-databaseds.$(KUBE_NAMESPACE).svc.$(CLUSTER_DOMAIN):10000

ifeq ($(CI_JOB_NAME_SLUG),lmc-acceptance-test)
k8s-test-runner: MARK = lmc
endif

-include .make/python.mk


#############################
# OCI, K8s, Helm
#############################
OCI_TAG = $(VERSION)-dev.c$(CI_COMMIT_SHORT_SHA)

CI_REGISTRY ?= registry.gitlab.com

# Use the previously built image when running in the pipeline
ifneq ($(CI_JOB_ID),)
CUSTOM_VALUES = --set dishmanager.image.image=$(NAME) \
	--set dishmanager.image.registry=$(CI_REGISTRY)/ska-telescope/$(NAME) \
	--set dishmanager.image.tag=$(OCI_TAG) \
	--set ska-mid-dish-simulators.enabled=true \
	--set ska-mid-dish-simulators.dsOpcuaSimulator.enabled=true \
	--set ska-mid-dish-simulators.deviceServers.spfdevice.enabled=true \
	--set ska-mid-dish-simulators.deviceServers.spfrxdevice.enabled=true \
	--set ska-mid-dish-ds-manager.enabled=true \
	--set ska-tango-base.enabled=true \
	--set global.dishes="{001,111}"
K8S_TEST_IMAGE_TO_TEST=$(CI_REGISTRY)/ska-telescope/$(NAME)/$(NAME):$(OCI_TAG)
K8S_TIMEOUT=600s
endif

K8S_CHART_PARAMS = --set global.minikube=$(MINIKUBE) \
	--set global.tango_host=$(TANGO_HOST) \
	--set global.operator=$(SKA_TANGO_OPERATOR) \
	--set global.cluster_domain=$(CLUSTER_DOMAIN) \
	$(CUSTOM_VALUES)

-include .make/oci.mk
-include .make/k8s.mk
-include .make/helm.mk


# include your own private variables for custom deployment configuration
-include PrivateRules.mak
