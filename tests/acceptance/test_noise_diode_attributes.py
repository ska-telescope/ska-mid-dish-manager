"""Test SPFRx noise diode attributes."""

from typing import Any

import numpy as np
import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import NoiseDiodeMode


@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.parametrize(
    ("attribute, valid_write_value"),
    [
        ("noiseDiodeMode", NoiseDiodeMode.PERIODIC),
        ("periodicnoisediodepars", np.array([1, 2, 3], dtype=np.int64)),
        ("pseudorandomnoisediodepars", np.array([1, 2, 3], dtype=np.int64)),
    ],
)
def test_set_noise_diode_attribute(
    dish_manager_proxy: tango.DeviceProxy,
    event_store_class: Any,
    attribute,
    valid_write_value,
) -> None:
    """Test set noise diode attribute."""
    event_store = event_store_class()
    dish_manager_proxy.subscribe_event(attribute, tango.EventType.CHANGE_EVENT, event_store)

    dish_manager_proxy.write_attribute(attribute, valid_write_value)
    event_store.wait_for_value(valid_write_value, timeout=7)
