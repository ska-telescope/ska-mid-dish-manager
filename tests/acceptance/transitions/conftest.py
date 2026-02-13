"""Fixtures for running ska-mid-dish-manager transition tests."""

import pytest


@pytest.fixture(autouse=True)
def setup_and_teardown(reset_dish_to_standby):
    """Reset the tango devices to a fresh state before each test."""
    yield
