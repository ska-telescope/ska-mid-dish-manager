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
    k_value = 5
    dish_manager_proxy.SetKValue(k_value)

    dm_event_store = event_store_class()
    spfrx_event_store = event_store_class()

    spfrx_device_proxy.subscribe_event("kValue", tango.EventType.CHANGE_EVENT, spfrx_event_store)
    spfrx_event_store.wait_for_value(k_value, timeout=7)

    # FIXME this is a workaround to force updates to be bubbled up to DishManager
    # It's not clear why attribute writes to sub component managers do not get
    # events flowing all through until this intervention is actioned
    dish_manager_proxy.SyncComponentStates()

    dish_manager_proxy.subscribe_event("kValue", tango.EventType.CHANGE_EVENT, dm_event_store)
    dm_event_store.wait_for_value(k_value, timeout=7)
