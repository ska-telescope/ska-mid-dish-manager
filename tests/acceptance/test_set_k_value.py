"""Test Set kvalue on SPFRx."""
from typing import Any

import pytest
import tango


@pytest.mark.acceptance
@pytest.mark.forked
def test_set_kvalue(
    dish_manager_proxy: tango.DeviceProxy,
    spfrx_device_proxy: tango.DeviceProxy,
    event_store_class: Any,
) -> None:
    """Test SetKValue on SPFRx."""
    value = 5
    dish_manager_proxy.SetKValue(value)

    dm_model_event_store = event_store_class()
    spfrx_model_event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        "kvalue", tango.EventType.CHANGE_EVENT, dm_model_event_store
    )
    spfrx_device_proxy.subscribe_event(
        "kvalue", tango.EventType.CHANGE_EVENT, spfrx_model_event_store
    )
    dm_model_event_store.wait_for_value(value, timeout=7)
    spfrx_model_event_store.wait_for_value(value, timeout=7)
