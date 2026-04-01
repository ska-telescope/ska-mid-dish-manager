"""Test the DishManager healthInfo attribute."""

import pytest
import tango
from ska_control_model import HealthState


@pytest.mark.acceptance
def test_healthinfo(dish_manager_proxy, spfrx_device_proxy, event_store_class):
    """Test the healthInfo attribute."""
    event_store = event_store_class()
    sub_id = dish_manager_proxy.subscribe_event(
        "healthInfo", tango.EventType.CHANGE_EVENT, event_store
    )
    event_store.clear_queue()

    spfrx_device_proxy.write_attribute("healthState", HealthState.OK)
    event_store.wait_for_value((), timeout=10)
    spfrx_device_proxy.write_attribute("healthState", HealthState.FAILED)
    event_store.wait_for_value(
        ('mid-dish/simulator-spfrx/SKA001: ["Unknown failure reason"]',), timeout=10
    )
    spfrx_device_proxy.write_attribute("healthState", HealthState.DEGRADED)
    event_store.wait_for_value(
        ('mid-dish/simulator-spfrx/SKA001: ["Unknown degraded reason"]',), timeout=10
    )

    spfrx_device_proxy.write_attribute("healthState", HealthState.OK)
    dish_manager_proxy.unsubscribe_event(sub_id)
