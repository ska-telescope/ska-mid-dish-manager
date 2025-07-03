CUSTOM_VALUES = --set global.minikube=$(MINIKUBE) \
	--set global.operator=false

VALUES_FILE = charts/ska-mid-dish-manager/custom_values.yaml

ifeq ($(GITLAB_CI),false)
K8S_CHART_PARAMS = $(CUSTOM_VALUES) \
	--values $(VALUES_FILE)
endif
