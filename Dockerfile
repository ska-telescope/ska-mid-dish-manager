ARG BUILD_IMAGE="artefact.skao.int/ska-tango-images-pytango-builder:9.3.14"
ARG BASE_IMAGE="artefact.skao.int/ska-tango-images-pytango-runtime:9.3.14"
FROM $BUILD_IMAGE AS buildenv

FROM $BASE_IMAGE

# install poetry
USER root
RUN pip3 install poetry
RUN apt-get update && apt-get install -y git

COPY pyproject.toml poetry.lock* ./

# install runtime dependencies and the app
RUN poetry config virtualenvs.create false && poetry install

USER tango

RUN ipython profile create
