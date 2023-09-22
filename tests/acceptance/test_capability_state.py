"""Test CapabilityState"""
import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import CapabilityStates
from tests.utils import EventStore


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_capability_state_b1(
    monitor_tango_servers, event_store, dish_manager_proxy, spf_device_proxy, spfrx_device_proxy
):
    """Test transition on CapabilityState b1"""
    dish_manager_proxy.subscribe_event(
        "b1CapabilityState",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    event_store.clear_queue()

    spf_event_store = EventStore()
    spf_device_proxy.subscribe_event(
        "b1CapabilityState",
        tango.EventType.CHANGE_EVENT,
        spf_event_store,
    )
    spf_event_store.clear_queue()

    spfrx_event_store = EventStore()
    spfrx_device_proxy.subscribe_event(
        "b1CapabilityState",
        tango.EventType.CHANGE_EVENT,
        spfrx_event_store,
    )
    spfrx_event_store.clear_queue()

    dish_manager_proxy.SetStandbyFPMode()

    event_store.wait_for_value(CapabilityStates.STANDBY, timeout=8)
