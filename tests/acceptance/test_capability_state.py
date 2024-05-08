"""Test CapabilityState"""
import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import CapabilityStates


# pylint:disable=unused-argument
@pytest.mark.acceptance
@pytest.mark.forked
def test_capability_state_b1(monitor_tango_servers, event_store_class, dish_manager_proxy):
    """Test transition on CapabilityState b1"""
    cap_state_event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        "b1CapabilityState",
        tango.EventType.CHANGE_EVENT,
        cap_state_event_store,
    )

    dish_manager_proxy.SetStandbyFPMode()
    cap_state_event_store.wait_for_value(CapabilityStates.STANDBY, timeout=10)
