ARG BUILD_IMAGE=artefact.skao.int/ska-build-python:0.1.1
ARG BASE_IMAGE=artefact.skao.int/ska-tango-images-tango-python:0.1.0
FROM $BUILD_IMAGE as build

# Set up environment variables for Poetry and virtualenv configuration
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1

WORKDIR /build

# Copy project dependency files (pyproject.toml, poetry.lock, etc.)
COPY pyproject.toml poetry.lock* README.md ./

# Install third-party dependencies from PyPI and CAR
RUN poetry install --no-root --no-directory

# Copy the source code and install only the application code
COPY src/ ./src
RUN poetry install --only main

# Use the base image for the final stage
FROM $BASE_IMAGE

WORKDIR /app

# Set up virtual environment path
ENV VIRTUAL_ENV=/build/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy the virtual environment from the build stage
COPY --from=build ${VIRTUAL_ENV} ${VIRTUAL_ENV}

# Add source code to the PYTHONPATH so Python can locate the package
COPY ./src/ska_mid_dish_manager ./ska_mid_dish_manager
ENV PYTHONPATH=${PYTHONPATH}:/app/

# Metadata labels
LABEL int.skao.image.team="TEAM KAROO" \
      int.skao.image.authors="samuel.twum@skao.int" \
      int.skao.image.url="https://gitlab.com/ska-telescope/ska-mid-dish-manager" \
      description="Tango device which provides master control and rolled-up monitoring of dish" \
      license="BSD-3-Clause"
