#############################
# BASE
#############################
NAME=ska-mid-dish-manager
VERSION=$(shell grep -e "^version = s*" pyproject.toml | cut -d = -f 2 | xargs)
TANGO_HOST ?= tango-databaseds:10000  ## TANGO_HOST connection to the Tango DS
CLUSTER_DOMAIN ?= cluster.local ## Domain used for naming Tango Device Servers
# values.yaml shall be used as the default and variables can be overridden by the user
# by defining them in the custom_helm_flags.yaml file
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
PYTHON_VARS_AFTER_PYTEST ?= -m '$(MARK)' --json-report --json-report-file=build/report.json --junitxml=build/report.xml --event-storage-files-path="build/events" --pointing-files-path=build/pointing

K8S_TEST_RUNNER_MARK ?= acceptance and (not transition)

python-test: MARK = unit and (not forked)
k8s-test-runner: MARK = $(K8S_TEST_RUNNER_MARK)
k8s-test-runner: TANGO_HOST = tango-databaseds.$(KUBE_NAMESPACE).svc.$(CLUSTER_DOMAIN):10000

-include .make/python.mk

python-test-forked: MARK = forked
python-test-forked: PYTHON_VARS_AFTER_PYTEST += --forked
python-test-forked: python-pre-test python-do-test python-post-test

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
CUSTOM_VALUES = --set dishmanager.image.image=$(NAME) \
	--set dishmanager.image.registry=$(CI_REGISTRY)/ska-telescope/mid-dish/$(NAME) \
	--set dishmanager.image.tag=$(OCI_TAG)
K8S_TIMEOUT=600s

K8S_CHART_PARAMS = --set global.tango_host=$(TANGO_HOST) \
	--set global.cluster_domain=$(CLUSTER_DOMAIN) \
	$(CUSTOM_VALUES) \
	--values $(VALUES_FILE)

-include .make/oci.mk
-include .make/k8s.mk
-include .make/helm.mk

# include your own private variables to add custom deployment configuration
-include PrivateRules.mak

#############################
# SIMLIB DOC GENERATION
#############################
NAMESPACE_SIMLIB=dish-manager
POD_SIMLIB=ds-dishmanager-001-0
DEVICE_DM  = mid-dish/dish-manager/SKA001
DEVICE_DS  = mid-dish/ds-manager/SKA001
DEVICE_SPF = mid-dish/simulator-spfc/SKA001
DEVICE_SPFRX = mid-dish/simulator-spfrx/SKA001
DEVICE_B5DC = mid-dish/b5dc-manager/SKA001
# Default device
DEVICE ?= DM
# Get the full name dynamically
FULL_DEVICE = $(DEVICE_$(DEVICE))
# Output filename based on DEVICE
DOC_OUTPUT = docs_$(DEVICE).yaml
# List of allowed devices
VALID_DEVICES = DM DS SPF SPFRX B5DC

simlib:
	@# Check device validity of device parameter
	@if ! echo $(VALID_DEVICES) | grep -wq $(DEVICE); then \
	    echo "ERROR: Invalid DEVICE='$(DEVICE)'. Must be one of: $(VALID_DEVICES)"; \
	    exit 1; \
	fi

	@echo "Generating docs for $(FULL_DEVICE) ..."
	@kubectl exec -n $(NAMESPACE_SIMLIB) $(POD_SIMLIB) -- \
	  tango-yaml tango_device $(FULL_DEVICE) > $(DOC_OUTPUT) 2> doc_errors.log
	@touch doc_errors.log
	@echo "Docs generated called: $(DOC_OUTPUT)"
	@echo "Errors (stderr) logged to doc_errors.log (if any)"