"""Test Set kvalue on SPFRx."""

from typing import Any

import pytest
import tango


@pytest.mark.fast
@pytest.mark.acceptance
def test_set_kvalue(
    dish_manager_proxy: tango.DeviceProxy,
    spfrx_device_proxy: tango.DeviceProxy,
    event_store_class: Any,
) -> None:
    """Test SetKValue on SPFRx."""
    k_value = 5
    dish_manager_proxy.SetKValue(k_value)

    dm_event_store = event_store_class()
    spfrx_event_store = event_store_class()

    sub_id = spfrx_device_proxy.subscribe_event(
        "kValue", tango.EventType.CHANGE_EVENT, spfrx_event_store
    )
    spfrx_event_store.wait_for_value(k_value, timeout=7)
    spfrx_device_proxy.unsubscribe_event(sub_id)

    sub_id = dish_manager_proxy.subscribe_event(
        "kValue", tango.EventType.CHANGE_EVENT, dm_event_store
    )
    dm_event_store.wait_for_value(k_value, timeout=7)
    dish_manager_proxy.unsubscribe_event(sub_id)
