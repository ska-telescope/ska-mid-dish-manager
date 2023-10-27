"""Test Set kvalue on SPFRx."""
from typing import Any

import pytest
import tango

from tests.utils import EventStore


@pytest.mark.acceptance
@pytest.mark.forked
def test_set_k_value(dish_manager_proxy: tango.DeviceProxy, event_store_class: Any) -> None:
    """Test Set kvalue on SPFRx."""
    value = 5
    dish_manager_proxy.SetKValue(value)

    model_event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        "SetKValue", tango.EventType.CHANGE_EVENT, model_event_store
    )
    model_event_store.wait_for_value(value, timeout=7)
