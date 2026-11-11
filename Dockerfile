FROM artefact.skao.int/ska-python-py314:1.1.4 AS runtime
FROM artefact.skao.int/ska-tango-images-tango-dsconfig:1.8.7 AS tools

FROM artefact.skao.int/ska-build-python-ubuntu26:1.1.4 AS build

# Build the venv with the exact interpreter the runtime image uses
COPY --from=runtime /opt/python /opt/python
ENV UV_NO_DEV=1 \
    UV_PYTHON=/opt/python/cpython-3.14.4-linux-x86_64-gnu/bin/python3.14 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY README.md pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project

COPY src /app/src
RUN uv sync --locked

FROM runtime
WORKDIR /app

ENV VIRTUAL_ENV=/app/.venv
COPY --from=build ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY --from=build /app/src /app/src
COPY --from=tools /usr/local/bin/retry /usr/local/bin/retry
COPY --from=tools /usr/local/bin/wait-for-it.sh /usr/local/bin/wait-for-it.sh

ENV PATH="$PATH:$VIRTUAL_ENV/bin"
ENV PYTHONPATH="/app/src"

# Metadata labels
LABEL int.skao.image.team="TEAM KAROO" \
      int.skao.image.authors="TEAM KAROO" \
      int.skao.image.url="https://gitlab.com/ska-telescope/ska-mid-dish-manager" \
      description="Tango device which provides master control and rolled-up monitoring of dish" \
      license="BSD-3-Clause"
