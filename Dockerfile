FROM artefact.skao.int/ska-tango-images-tango-dsconfig:1.8.7 as tools
FROM artefact.skao.int/ska-build-python-ubuntu26:1.0.0 as build

ENV UV_NO_DEV=1

WORKDIR /app

COPY README.md pyproject.toml uv.lock ./

RUN uv sync --locked --no-install-project

COPY README.md ./
COPY src /app/src

RUN uv sync --locked

FROM artefact.skao.int/ska-python-py314:1.0.0
WORKDIR /app

ENV VIRTUAL_ENV=/app/.venv
COPY --from=build ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY --from=build /app/src /app/src
COPY --from=tools /usr/local/bin/retry /usr/local/bin/retry
COPY --from=tools /usr/local/bin/wait-for-it.sh /usr/local/bin/wait-for-it.sh

# Override the default python
RUN rm /app/.venv/bin/python
RUN rm /app/.venv/bin/python3
RUN ln -s  /usr/local/bin/python3   /app/.venv/bin/python3


ENV PATH="$PATH:$VIRTUAL_ENV/bin"
ENV PYTHONPATH="/app/src:/app/.venv/lib/python3.14/site-packages/:${PYTHONPATH}"

# Metadata labels
LABEL int.skao.image.team="TEAM KAROO" \
      int.skao.image.authors="TEAM KAROO" \
      int.skao.image.url="https://gitlab.com/ska-telescope/ska-mid-dish-manager" \
      description="Tango device which provides master control and rolled-up monitoring of dish" \
      license="BSD-3-Clause"
