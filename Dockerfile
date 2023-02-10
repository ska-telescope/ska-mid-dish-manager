ARG BUILD_IMAGE="artefact.skao.int/ska-tango-images-pytango-builder:9.3.34"
ARG BASE_IMAGE="artefact.skao.int/ska-tango-images-pytango-runtime:9.3.21"
FROM $BUILD_IMAGE AS buildenv

FROM $BASE_IMAGE
USER root

ENV KUBECTL_VERSION="v1.25.6"
ENV HELM_VERSION="v3.11.0"

RUN apt-get update && apt-get install -y --no-install-recommends wget
## install kubectl and helm
RUN wget -q https://storage.googleapis.com/kubernetes-release/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl -O /usr/local/bin/kubectl \
    && chmod +x /usr/local/bin/kubectl \
    && wget -q https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz -O - | tar -xzO linux-amd64/helm > /usr/local/bin/helm \
    && chmod +x /usr/local/bin/helm

# Make sure there's no venv
RUN rm -rf /home/tango/.cache/pypoetry/virtualenvs/*

COPY pyproject.toml poetry.lock* ./
# install runtime dependencies and the app
RUN poetry config virtualenvs.create false && poetry install

USER tango
