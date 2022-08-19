"""Test StandbyLP"""
import pytest
import tango

from ska_mid_dish_manager.devices.test_devices.utils import (
    EventStore,
    set_dish_manager_to_standby_lp,
)
from ska_mid_dish_manager.models.dish_enums import (
    CapabilityStates,
    DishMode,
    DSOperatingMode,
    SPFCapabilityStates,
    SPFRxCapabilityStates,
)


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_capability_state_b1(
    event_store, dish_manager_proxy, spf_device_proxy, spfrx_device_proxy
):
    """Test transition on CapabilityState b1"""
    set_dish_manager_to_standby_lp(event_store, dish_manager_proxy)
    assert dish_manager_proxy.dishMode == DishMode.STANDBY_LP
    assert dish_manager_proxy.b1CapabilityState != CapabilityStates.STANDBY

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

    assert dish_manager_proxy.b1CapabilityState != CapabilityStates.STANDBY

    # Ensure updates
    if spfrx_device_proxy.b1CapabilityState == SPFRxCapabilityStates.OPERATE:
        spfrx_device_proxy.b1CapabilityState = (
            SPFRxCapabilityStates.UNAVAILABLE
        )
    spfrx_device_proxy.b1CapabilityState = SPFRxCapabilityStates.OPERATE
    spfrx_event_store.wait_for_value(SPFRxCapabilityStates.OPERATE)

    if (
        spf_device_proxy.b1CapabilityState
        == SPFCapabilityStates.OPERATE_DEGRADED
    ):
        spf_device_proxy.b1CapabilityState = SPFCapabilityStates.OPERATE_FULL
    spf_device_proxy.b1CapabilityState = SPFCapabilityStates.OPERATE_DEGRADED
    spf_event_store.wait_for_value(SPFCapabilityStates.OPERATE_DEGRADED)

    event_store.wait_for_value(CapabilityStates.STANDBY, timeout=8)


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_capability_state_b2(
    event_store,
    dish_manager_proxy,
    spf_device_proxy,
    spfrx_device_proxy,
    ds_device_proxy,
):
    """Test transition on CapabilityState b2"""
    ds_device_proxy.operatingMode = DSOperatingMode.STARTUP
    spf_device_proxy.b1CapabilityState = SPFCapabilityStates.UNAVAILABLE
    spfrx_device_proxy.b1CapabilityState = SPFRxCapabilityStates.UNAVAILABLE

    dish_manager_proxy.subscribe_event(
        "b2CapabilityState",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    event_store.wait_for_value(CapabilityStates.UNAVAILABLE, timeout=8)
