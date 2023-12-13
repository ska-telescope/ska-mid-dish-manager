
LOCAL_DEPLOYMENT = --set global.minikube=$(MINIKUBE) \
	--set global.operator=$(SKA_TANGO_OPERATOR) \
	--set ska-mid-dish-simulators.enabled=true \
	--set ska-mid-dish-simulators.dsOpcuaSimulator.enabled=true \
	--set ska-mid-dish-simulators.deviceServers.spfdevice.enabled=true \
	--set ska-mid-dish-simulators.deviceServers.spfrxdevice.enabled=true \
	--set ska-mid-dish-ds-manager.enabled=true \
	--set ska-tango-base.enabled=true

ifeq ($(GITLAB_CI),false)
K8S_CHART_PARAMS = $(LOCAL_DEPLOYMENT)
endif
