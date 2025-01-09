ARG BUILD_IMAGE=artefact.skao.int/ska-build-python:0.1.1
ARG BASE_IMAGE=artefact.skao.int/ska-tango-images-tango-python:0.1.0
FROM $BUILD_IMAGE as build

WORKDIR /src

COPY pyproject.toml poetry.lock* ./

ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=1
ENV POETRY_VIRTUALENVS_CREATE=1

# no-root is required because in the build
# step we only want to install dependencies
# not the code under development
RUN poetry install --no-root

FROM $BASE_IMAGE

WORKDIR /src

# Adding the virtualenv binaries
# to the PATH so there is no need
# to activate the venv
ENV VIRTUAL_ENV=/src/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY --from=build ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY ./src/ska_mid_dish_manager ./ska_mid_dish_manager

# Add source code to the PYTHONPATH
# so python is able to find our package
# when we use it on imports
ENV PYTHONPATH=${PYTHONPATH}:/src/

LABEL int.skao.image.team="TEAM KAROO" \
      int.skao.image.authors="TEAM KAROO" \
      int.skao.image.url="https://gitlab.com/ska-telescope/ska-mid-dish-manager" \
      description="Tango device which provides master control and rolled-up monitoring of dish." \
      license="BSD-3-Clause"
