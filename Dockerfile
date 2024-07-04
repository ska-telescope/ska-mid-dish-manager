FROM artefact.skao.int/ska-tango-images-pytango-builder:9.5.0 AS buildenv
FROM artefact.skao.int/ska-tango-images-pytango-runtime:9.5.0 AS runtime

USER root

# Make sure there's no venv
RUN rm -rf /home/tango/.cache/pypoetry/virtualenvs/*

COPY pyproject.toml poetry.lock* ./
# install runtime dependencies and the app
RUN poetry config virtualenvs.create false && poetry install

USER tango
