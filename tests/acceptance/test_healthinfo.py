"""Test the DishManager healthInfo attribute."""

import pytest
import tango
from ska_control_model import HealthState

from ska_mid_dish_manager.models.dish_enums import SPFHealthState


@pytest.mark.acceptance
def test_healthinfo(dish_manager_proxy, spfrx_device_proxy, spf_device_proxy, event_store_class):
    """Test the healthInfo attribute."""
    event_store = event_store_class()
    sub_id = dish_manager_proxy.subscribe_event(
        "healthInfo", tango.EventType.CHANGE_EVENT, event_store
    )
    spfrx_device_proxy.write_attribute("healthState", HealthState.OK)
    spf_device_proxy.write_attribute("healthState", SPFHealthState.NORMAL)

    event_store.wait_for_value((), timeout=10)
    spfrx_device_proxy.write_attribute("healthState", HealthState.FAILED)
    # Added to ensure that healthInfo doesn't throw a data size error when more
    #  than 1 healthinfo update is received.
    spf_device_proxy.write_attribute("healthState", SPFHealthState.DEGRADED)

    event_store.wait_for_value(
        (
            'mid-dish/simulator-spfc/SKA001: ["Unknown degraded reason"]',
            'mid-dish/simulator-spfrx/SKA001: ["Unknown failure reason"]',
        ),
        timeout=10,
    )
    spf_device_proxy.write_attribute("healthState", SPFHealthState.NORMAL)
    spfrx_device_proxy.write_attribute("healthState", HealthState.DEGRADED)
    event_store.wait_for_value(
        ('mid-dish/simulator-spfrx/SKA001: ["Unknown degraded reason"]',), timeout=10
    )

    spfrx_device_proxy.write_attribute("healthState", HealthState.OK)
    dish_manager_proxy.unsubscribe_event(sub_id)
