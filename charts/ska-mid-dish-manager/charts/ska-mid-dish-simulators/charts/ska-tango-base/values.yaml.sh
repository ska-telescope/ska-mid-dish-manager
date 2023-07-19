#!/bin/bash

RELEASE_SUPPORT="${RELEASE_SUPPORT:-../../.make/.make-release-support}"
VALUES_YAML=values.yaml
CAR_OCI_REGISTRY_HOST="${CAR_OCI_REGISTRY_HOST:-artefact.skao.int}"
CI_COMMIT_SHORT_SHA="${CI_COMMIT_SHORT_SHA:-blah}"
SUFFIX=""

# Disabled this as it complicates the rules: changes: - pxh 30/09/2021
# Check if this is a dev build
# if [[ "${CAR_OCI_REGISTRY_HOST}" == registry.gitlab.com* ]] || [[ -z "${CAR_OCI_REGISTRY_HOST}" ]]; then
#     SUFFIX="-dev.${CI_COMMIT_SHORT_SHA}"  #"-" is used as "+" causes the docker building process to fail
# fi

cat <<EOF > ${VALUES_YAML}
# Default values for tango-base.
# This is a YAML-formatted file.
# Declare variables to be passed into your templates.

# global:
#   annotations:
#     app.gitlab.com/app: CI_PROJECT_PATH_SLUG
#     app.gitlab.com/env: CI_ENVIRONMENT_SLUG
  # by setting this parameter we can disable the lower level sub-system tango-base, archiver and webjive
  # sub-system:
  #   tango-base:
  #     enabled: false
  #   archiver:
  #     enabled: false
  #   webjive:
  #     enabled: false

# tango-base:
#   enabled: true


# Default values for tango-base.
# This is a YAML-formatted file.
# Declare variables to be passed into your templates.

display: ":0"
xauthority: "~/.Xauthority"

global:
  minikube: false
  exposeDatabaseDS: false
  exposeAllDS: false
  cluster_domain: cluster.local
  tango_host: databaseds-tango-base:10000
  databaseds_port: 10000
  databaseds_ip: "0.0.0.0"
  device_server_port: 45450
  retry:
  - "--sleep=1"
  - "--tries=100"

homeDir: /home/ubuntu
system: SW-infrastructure
subsystem: ska-tango-base
telescope: SKA-mid

labels:
  app: ska-tango-images

dsconfig:
  image:
    registry: ${CAR_OCI_REGISTRY_HOST}
    image: ska-tango-images-tango-dsconfig
    tag: $(. ${RELEASE_SUPPORT}; RELEASE_CONTEXT_DIR=../../images/ska-tango-images-tango-dsconfig setContextHelper; getVersion)${SUFFIX}
    pullPolicy: IfNotPresent

itango:
  enabled: false
  component: itango-console
  function: generic-tango-console
  domain: interactive-testing
  intent: enabling
  image:
    registry: ${CAR_OCI_REGISTRY_HOST}
    image: ska-tango-images-tango-itango
    tag: $(. ${RELEASE_SUPPORT}; RELEASE_CONTEXT_DIR=../../images/ska-tango-images-tango-itango setContextHelper; getVersion)${SUFFIX}
    pullPolicy: IfNotPresent
  resources:
    requests:
      cpu: 100m     # 00m = 0.1 CPU
      memory: 128Mi # 128Mi = 0.125 GB mem
      ephemeral-storage: 512Mi
    limits:
      cpu: 100m     # 00m = 0.1 CPU
      memory: 128Mi # 128Mi = 0.125 GB mem
      ephemeral-storage: 512Mi

databaseds:
  component: databaseds
  function: tangodb-interface
  domain: tango-configuration
  intent: production
  image:
    registry: ${CAR_OCI_REGISTRY_HOST}
    image: ska-tango-images-tango-cpp
    tag: $(. ${RELEASE_SUPPORT}; RELEASE_CONTEXT_DIR=../../images/ska-tango-images-tango-cpp setContextHelper; getVersion)${SUFFIX}
    pullPolicy: IfNotPresent
  vault:
    useVault: false
    secretPath: stfc
    role: kube-role    
  resources:
    requests:
      cpu: 100m     # 100m = 0.1 CPU
      memory: 128Mi # 128Mi = 0.125 GB mem
      ephemeral-storage: 512Mi
    limits:
      cpu: 300m     # 300m = 0.3 CPU
      memory: 256Mi # 256Mi = 0.25 GB mem
      ephemeral-storage: 1Gi
  livenessProbe:
    enabled: true
    initialDelaySeconds: 0
    periodSeconds: 10
    timeoutSeconds: 1
    successThreshold: 1
    failureThreshold: 3
  readinessProbe:
    enabled: true
    initialDelaySeconds: 0
    periodSeconds: 10
    timeoutSeconds: 1
    successThreshold: 1
    failureThreshold: 3

deviceServers:
  tangotest:
    name: tangotest
    function: tango-test
    domain: tango-base
    command: "/usr/local/bin/TangoTest"
    instances: ["test"]
    environment_variables: []
    server:
      name: "TangoTest"
      instances:
      - name: "test"
        classes:
        - name: "TangoTest"
          devices:
          - name: "sys/tg_test/1"
    image:
      registry: ${CAR_OCI_REGISTRY_HOST}
      image: ska-tango-images-tango-java
      tag: $(. ${RELEASE_SUPPORT}; RELEASE_CONTEXT_DIR=../../images/ska-tango-images-tango-java setContextHelper; getVersion)${SUFFIX}
      pullPolicy: IfNotPresent
    resources:
      requests:
        cpu: 200m     # 200m = 0.2 CPU
        memory: 256Mi # 256Mi = 0.25 GB mem
        ephemeral-storage: 1Gi
      limits:
        cpu: 500m     # 500m = 0.5 CPU
        memory: 512Mi # 512Mi = 0.5 GB mem
        ephemeral-storage: 1Gi
    livenessProbe:
      initialDelaySeconds: 0
      periodSeconds: 10
      timeoutSeconds: 1
      successThreshold: 1
      failureThreshold: 3
    readinessProbe:
      initialDelaySeconds: 0
      periodSeconds: 10
      timeoutSeconds: 1
      successThreshold: 1
      failureThreshold: 3

tangodb:
  enabled: true
  use_pv: false
  component: tangodb
  function: tango-device-configuration
  domain: tango-configuration
  intent: production
  image:
    registry: ${CAR_OCI_REGISTRY_HOST}
    image: ska-tango-images-tango-db
    tag: $(. ${RELEASE_SUPPORT}; RELEASE_CONTEXT_DIR=../../images/ska-tango-images-tango-db setContextHelper; getVersion)${SUFFIX}
    pullPolicy: IfNotPresent
  db:
    rootpw: secret
    db: tango
    user: tango
    password: tango
  vault:
    useVault: false
    secretPath: stfc
    role: kube-role
  resources:
    requests:
      cpu: 100m     # 100m = 0.1 CPU
      memory: 256Mi # 256Mi = 0.25 GB mem
      ephemeral-storage: 1Gi
    limits:
      cpu: 200m     # 200m = 0.2 CPU
      memory: 256Mi # 256Mi = 0.25 GB mem
      ephemeral-storage: 2Gi
  livenessProbe:
    enabled: false
    initialDelaySeconds: 10
    periodSeconds: 10
    timeoutSeconds: 1
    successThreshold: 1
    failureThreshold: 3
  readinessProbe:
    enabled: false
    initialDelaySeconds: 10
    periodSeconds: 10
    timeoutSeconds: 1
    successThreshold: 1
    failureThreshold: 3

vnc:
  enabled: false
  component: vnc-gui
  function: generic-tango-vnc-gui
  domain: interactive-testing
  intent: enabling
  nodeport_enabled: false
  nodeport_vnc: 32081
  nodeport_novnc: 32082
  replicas: 3
  image:
    registry: ${CAR_OCI_REGISTRY_HOST}
    image: ska-tango-images-tango-vnc
    tag: $(. ${RELEASE_SUPPORT}; RELEASE_CONTEXT_DIR=../../images/ska-tango-images-tango-vnc setContextHelper; getVersion)${SUFFIX}
    pullPolicy: IfNotPresent
  resources:
    requests:
      cpu: 100m     # 100m = 0.1 CPU
      memory: 256Mi # 256Mi = 0.25 GB mem
      ephemeral-storage: 256Mi
    limits:
      cpu: 100m     # 100m = 0.1 CPU
      memory: 256Mi # 256Mi = 0.25 GB mem
      ephemeral-storage: 256Mi

# Configure Ingress resource that allow you to access the Tango REST API
ingress:
  enabled: true
  nginx: true

nodeSelector: {}

affinity: {}

tolerations: []

EOF
