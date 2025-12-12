"""Test attenuation attributes on SPFRx."""

from typing import Any

import pytest
import tango


@pytest.mark.acceptance
@pytest.mark.parametrize(
    "tango_attribute, sensor_value",
    [
        ("attenuation1polhx", 1.0),
        ("attenuation1polvy", 2.0),
        ("attenuation2polhx", 3.0),
        ("attenuation2polvy", 4.0),
        ("attenuationpolhx", 5.0),
        ("attenuationpolvy", 6.0),
    ],
)
def test_attenuation_attrs(
    tango_attribute: str,
    sensor_value: Any,
    dish_manager_proxy: tango.DeviceProxy,
    spfrx_device_proxy: tango.DeviceProxy,
    event_store_class: Any,
) -> None:
    """Test attenuation attributes on SPFRx."""
    dm_event_store = event_store_class()

    sub_id = dish_manager_proxy.subscribe_event(
        tango_attribute, tango.EventType.CHANGE_EVENT, dm_event_store
    )
    spfrx_device_proxy.write_attribute(tango_attribute, sensor_value)

    dm_event_store.wait_for_value(sensor_value, timeout=7)
    dish_manager_proxy.unsubscribe_event(sub_id)
