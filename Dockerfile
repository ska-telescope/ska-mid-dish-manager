FROM artefact.skao.int/ska-tango-images-pytango-builder:9.5.0 AS buildenv
FROM artefact.skao.int/ska-tango-images-pytango-runtime:9.5.0 AS runtime

USER root

COPY pyproject.toml poetry.lock* ./
COPY pytango-9.5.0-cp310-cp310-manylinux_2_35_x86_64.whl ./

RUN poetry config virtualenvs.create false

# Only install dependencies, this layer should be cached until
# pyproject.toml poetry.lock changes
RUN poetry install --no-root

COPY . .

RUN poetry install --only-root

RUN pip install --force-reinstall pytango-9.5.0-cp310-cp310-manylinux_2_35_x86_64.whl

USER tango
