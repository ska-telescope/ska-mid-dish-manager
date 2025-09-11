"""Data for tests."""

import importlib.resources

from tests import data

RADIAL_SCAN_CSV_PATH = importlib.resources.files(data) / "radial.csv"
SPIRAL_SCAN_CSV_PATH = importlib.resources.files(data) / "spiral.csv"
SIDEREAL_SCAN_CSV_PATH = importlib.resources.files(data) / "sidereal_tt_3mins.csv"
UP_DOWN_SCAN_CSV_PATH = importlib.resources.files(data) / "UpDownleftRight_no_tai.csv"
CORDIODSCAN__CSV_PATH = importlib.resources.files(data) / "cardioid_scan.csv"
RASTER_SCAN_CSV_PATH = importlib.resources.files(data) / "raster_scan.csv"
