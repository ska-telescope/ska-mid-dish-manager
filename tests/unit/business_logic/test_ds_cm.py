"""Unit tests for DS component manager."""

import logging
from threading import Lock
from unittest import mock

import pytest

from ska_mid_dish_manager.component_managers.ds_cm import DSComponentManager

LOGGER = logging.getLogger(__name__)


@pytest.mark.unit
def test_ds_component_manager_includes_buildstate_in_monitored_attributes() -> None:
    """DSComponentManager should monitor buildState (lowercased as buildstate)."""
    cm = DSComponentManager(
        "a/b/c",
        LOGGER,
        Lock(),
        communication_state_callback=mock.Mock(),
        component_state_callback=mock.Mock(),
    )

    assert "buildstate" in cm._monitored_attributes
