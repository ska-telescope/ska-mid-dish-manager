ARG BUILD_IMAGE="artefact.skao.int/ska-tango-images-pytango-builder:9.3.32"
ARG BASE_IMAGE="artefact.skao.int/ska-tango-images-pytango-runtime:9.3.19"
FROM $BUILD_IMAGE AS buildenv

FROM $BASE_IMAGE

USER root
COPY pyproject.toml poetry.lock* ./

# install runtime dependencies and the app
RUN poetry config virtualenvs.create false && poetry install

USER tango
