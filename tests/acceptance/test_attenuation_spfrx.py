"""Test attenuation attributes on SPFRx."""

from random import randint
from typing import Any

import pytest
import tango


@pytest.mark.fast
@pytest.mark.acceptance
@pytest.mark.parametrize(
    "tango_attribute",
    [
        ("attenuation1PolHX"),
        ("attenuation1PolVY"),
        ("attenuation2PolHX"),
        ("attenuation2PolVY"),
        ("attenuationPolHX"),
        ("attenuationPolVY"),
    ],
)
def test_attenuation_attrs(
    tango_attribute: str,
    dish_manager_proxy: tango.DeviceProxy,
    spfrx_device_proxy: tango.DeviceProxy,
    event_store_class: Any,
) -> None:
    """Test attenuation attributes on SPFRx."""
    dm_event_store = event_store_class()
    # Subscribe to the DishManager attribute change event to monitor updates
    sub_id = dish_manager_proxy.subscribe_event(
        tango_attribute, tango.EventType.CHANGE_EVENT, dm_event_store
    )
    current_value = spfrx_device_proxy.read_attribute(tango_attribute).value
    write_value = current_value + randint(1, 10)
    # Set the attenuation attribute on the SPFRx device
    dm_event_store.clear_queue()
    spfrx_device_proxy.write_attribute(tango_attribute, write_value)

    # Wait for the DishManager to receive the updated value
    dm_event_store.wait_for_value(write_value, timeout=10)
    dish_manager_proxy.unsubscribe_event(sub_id)
