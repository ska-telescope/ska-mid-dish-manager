FROM artefact.skao.int/ska-tango-images-tango-dsconfig:1.5.13 as tools
FROM artefact.skao.int/ska-build-python:0.3.1 as build

WORKDIR /app
COPY pyproject.toml poetry.lock ./

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=1
ENV POETRY_VIRTUALENVS_CREATE=1

RUN poetry install --no-root

COPY src /app/src
COPY README.md /app/README.md
RUN poetry install --only-root

FROM artefact.skao.int/ska-python:0.2.3
WORKDIR /app

ENV VIRTUAL_ENV=/app/.venv
COPY --from=build ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY --from=build /app/src /app/src
COPY --from=tools /usr/local/bin/retry /usr/local/bin/retry
COPY --from=tools /usr/local/bin/wait-for-it.sh /usr/local/bin/wait-for-it.sh

ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONPATH="/app/src:app/.venv/lib/python3.10/site-packages/:${PYTHONPATH}"

# open telemetry environment variables
ENV TANGO_TELEMETRY_ENABLE=on
ENV TANGO_TELEMETRY_TRACES_EXPORTER=grpc
# ENV TANGO_TELEMETRY_TRACES_ENDPOINT=grpc://test-signoz-otel-collector:4317
ENV TANGO_TELEMETRY_TRACES_ENDPOINT=grpc://localhost:4317
ENV TANGO_TELEMETRY_LOGS_EXPORTER=none


# Metadata labels
LABEL int.skao.image.team="TEAM KAROO" \
      int.skao.image.authors="TEAM KAROO" \
      int.skao.image.url="https://gitlab.com/ska-telescope/ska-mid-dish-manager" \
      description="Tango device which provides master control and rolled-up monitoring of dish" \
      license="BSD-3-Clause"
