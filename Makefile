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

-include .make/base.mk


#############################
# DOCS
#############################
-include .make/docs.mk


#############################
# PYTHON
#############################
# Set the specific environment variables required for pytest
ifeq ($(MAKECMDGOALS),python-test)
MARK = unit
endif

ifeq ($(MAKECMDGOALS),k8s-test-runner)
MARK = acceptance
TANGO_HOST = tango-databaseds.$(KUBE_NAMESPACE).svc.cluster.local:10000
endif

ifeq ($(MAKECMDGOALS),k8s-lmc-test)
MARK = lmc
TANGO_HOST = tango-databaseds.$(KUBE_NAMESPACE).svc.cluster.local:10000
endif

PYTHON_VARS_BEFORE_PYTEST ?= PYTHONPATH=.:./src \
							 TANGO_HOST=$(TANGO_HOST)

PYTHON_VARS_AFTER_PYTEST ?= -m '$(MARK)' --forked --json-report --json-report-file=build/report.json --junitxml=build/report.xml --cucumberjson=build/cucumber.json  --event-storage-files-path="build/events"

PYTHON_SWITCHES_FOR_BLACK ?= --line-length 99

PYTHON_SWITCHES_FOR_ISORT ?= -w 99

PYTHON_SWITCHES_FOR_FLAKE8 ?= --max-line-length=99

PYTHON_LINE_LENGTH ?= 99

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
	--set deviceServers.dsdevice.enabled=true \
	--set ska-mid-dish-simulators.deviceServers.spfdevice.enabled=true \
	--set ska-mid-dish-simulators.deviceServers.spfrxdevice.enabled=true
K8S_TEST_IMAGE_TO_TEST=$(CI_REGISTRY)/ska-telescope/$(NAME)/$(NAME):$(OCI_TAG)
endif

K8S_CHART_PARAMS = --set global.minikube=$(MINIKUBE) \
	--set global.tango_host=$(TANGO_HOST) \
	--set global.operator=$(SKA_TANGO_OPERATOR) \
	$(CUSTOM_VALUES)

-include .make/oci.mk
-include .make/k8s.mk
-include .make/helm.mk


# include your own private variables for custom deployment configuration
-include PrivateRules.mak


#############################
# make targets for ci file
#############################
k8s-lmc-test:
##  Cleanup
	@rm -fr build; mkdir build
	@find ./$(k8s_test_folder) -name "*.pyc" -type f -delete

##  Install requirements
	if [[ -f pyproject.toml ]]; then \
		poetry config virtualenvs.create false; \
		echo 'k8s-test: installing poetry dependencies';  \
		poetry install; \
	else if [[ -f $(k8s_test_folder)/requirements.txt ]]; then \
			echo 'k8s-test: installing $(k8s_test_folder)/requirements.txt'; \
			pip install -qUr $(k8s_test_folder)/requirements.txt; \
		fi; \
	fi;

##  Run tests
	export PYTHONPATH=${PYTHONPATH}:/app/src$(k8s_test_src_dirs)
	mkdir -p build
	cd $(K8S_RUN_TEST_FOLDER) && $(K8S_TEST_TEST_COMMAND); echo $$? > $(BASE)/build/status

##  Post tests reporting
	pip list > build/pip_list.txt
	@echo "k8s_test_command: test command exit is: $$(cat build/status)"
