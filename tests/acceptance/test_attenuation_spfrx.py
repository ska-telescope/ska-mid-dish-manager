"""Test attenuation attributes on SPFRx."""

from typing import Any

import pytest
import tango


@pytest.mark.acceptance
@pytest.mark.parametrize(
    "tango_attribute, write_value",
    [
        ("attenuation1PolHX", 1.0),
        ("attenuation1PolVY", 2.0),
        ("attenuation2PolHX", 3.0),
        ("attenuation2PolVY", 4.0),
        ("attenuationPolHX", 5.0),
        ("attenuationPolVY", 6.0),
    ],
)
def test_attenuation_attrs(
    tango_attribute: str,
    write_value: Any,
    dish_manager_proxy: tango.DeviceProxy,
    spfrx_device_proxy: tango.DeviceProxy,
    event_store_class: Any,
) -> None:
    """Test attenuation attributes on SPFRx."""
    dm_event_store = event_store_class()

    sub_id = dish_manager_proxy.subscribe_event(
        tango_attribute, tango.EventType.CHANGE_EVENT, dm_event_store
    )
    # Set the attenuation attribute on the SPFRx device
    spfrx_device_proxy.write_attribute(tango_attribute, write_value)

    # Wait for the DishManager to receive the updated value
    dm_event_store.wait_for_value(write_value, timeout=7)
    dish_manager_proxy.unsubscribe_event(sub_id)
