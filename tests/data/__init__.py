"""Data for tests."""

import importlib.resources

from tests import data

RADIAL_CSV_PATH = importlib.resources.files(data) / "radial.csv"
SPIRAL_CSV_PATH = importlib.resources.files(data) / "spiral.csv"
