ARG BUILD_IMAGE="artefact.skao.int/ska-tango-images-pytango-builder:9.3.34"
ARG BASE_IMAGE="artefact.skao.int/ska-tango-images-pytango-runtime:9.3.21"
FROM $BUILD_IMAGE AS buildenv

FROM $BASE_IMAGE
USER root

# Make sure there's no venv
RUN rm -rf /home/tango/.cache/pypoetry/virtualenvs/*

COPY pyproject.toml poetry.lock* ./
# install runtime dependencies and the app
RUN poetry config virtualenvs.create false && poetry install

USER tango
