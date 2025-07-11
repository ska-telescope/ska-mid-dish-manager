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
CLUSTER_DOMAIN ?= cluster.local ## Domain used for naming Tango Device Servers
VALUES_FILE ?= charts/ska-mid-dish-manager/custom_helm_flags.yaml

-include .make/base.mk


#############################
# DOCS
#############################
-include .make/docs.mk


#############################
# PYTHON
#############################
# set line length for all linters
PYTHON_LINE_LENGTH = 99

# Set the specific environment variables required for pytest
PYTHON_VARS_BEFORE_PYTEST ?= PYTHONPATH=.:./src \
							 TANGO_HOST=$(TANGO_HOST)
PYTHON_VARS_AFTER_PYTEST ?= -m '$(MARK)' --forked --json-report --json-report-file=build/report.json --junitxml=build/report.xml --event-storage-files-path="build/events" --pointing-files-path=build/pointing

K8S_TEST_RUNNER_MARK ?= acceptance

python-test: MARK = unit
k8s-test-runner: MARK = $(K8S_TEST_RUNNER_MARK)
k8s-test-runner: TANGO_HOST = tango-databaseds.$(KUBE_NAMESPACE).svc.$(CLUSTER_DOMAIN):10000

-include .make/python.mk

python-do-format:
	$(PYTHON_RUNNER) ruff format $(PYTHON_LINT_TARGET)
	$(PYTHON_RUNNER) ruff check --fix $(PYTHON_LINT_TARGET)

python-do-lint:
	@mkdir -p build/reports
	@rc=0; \
	set -x; \
	$(PYTHON_RUNNER) ruff format --check $(PYTHON_LINT_TARGET) || rc=1; \
	$(PYTHON_RUNNER) ruff check $(PYTHON_LINT_TARGET) || rc=1; \
	exit $$rc

ifdef CI_JOB_TOKEN
python-post-lint:
	$(PYTHON_RUNNER) ruff check --output-format="junit" --output-file=build/reports/linting-ruff.xml
	@make --no-print-directory join-lint-reports
endif

#############################
# OCI, K8s, Helm
#############################
OCI_TAG = $(VERSION)-dev.c$(CI_COMMIT_SHORT_SHA)

CI_REGISTRY ?= registry.gitlab.com

# Use the previously built image when running in the pipeline
ifneq ($(CI_JOB_ID),)
CUSTOM_VALUES = --set dishmanager.image.image=$(NAME) \
	--set dishmanager.image.registry=$(CI_REGISTRY)/ska-telescope/$(NAME) \
	--set dishmanager.image.tag=$(OCI_TAG)
K8S_TEST_IMAGE_TO_TEST=$(CI_REGISTRY)/ska-telescope/$(NAME)/$(NAME):$(OCI_TAG)
K8S_TIMEOUT=600s
endif

K8S_CHART_PARAMS = --set global.tango_host=$(TANGO_HOST) \
	--set global.cluster_domain=$(CLUSTER_DOMAIN) \
	$(CUSTOM_VALUES) \
	--values $(VALUES_FILE)

-include .make/oci.mk
-include .make/k8s.mk
-include .make/helm.mk


# include your own private variables for custom deployment configuration
-include PrivateRules.mak
