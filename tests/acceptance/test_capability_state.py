"""Test CapabilityState"""
import logging

import pytest
import tango

from ska_mid_dish_manager.devices.test_devices.utils import (
    EventStore,
    set_dish_manager_to_standby_lp,
)
from ska_mid_dish_manager.models.dish_enums import (
    CapabilityStates,
    DishMode,
    IndexerPosition,
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


# pylint: disable=too-many-arguments
@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_capability_state_b2(
    event_store_class,
    event_store,
    dish_manager_proxy,
    spf_device_proxy,
    spfrx_device_proxy,
    ds_device_proxy,
    caplog,
):
    """Test transition on CapabilityState b2"""
    set_dish_manager_to_standby_lp(event_store, dish_manager_proxy)
    caplog.set_level(logging.DEBUG)

    # Force to known non configuring state
    spf_device_proxy.b2CapabilityState = SPFCapabilityStates.STANDBY
    ds_device_proxy.indexerPosition = IndexerPosition.MOVING
    spfrx_device_proxy.b2CapabilityState = SPFRxCapabilityStates.STANDBY

    # Wait for spfrx change
    spfrx_events = event_store_class()
    spfrx_device_proxy.subscribe_event(
        "b2CapabilityState",
        tango.EventType.CHANGE_EVENT,
        spfrx_events,
    )
    spfrx_events.wait_for_value(SPFRxCapabilityStates.STANDBY)

    spf_events = event_store_class()
    spf_device_proxy.subscribe_event(
        "b2CapabilityState",
        tango.EventType.CHANGE_EVENT,
        spf_events,
    )
    spf_events.wait_for_value(SPFCapabilityStates.STANDBY)

    # Check dish_manager
    dish_manager_proxy.subscribe_event(
        "b2CapabilityState",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    event_store.wait_for_value(SPFCapabilityStates.STANDBY)

    spf_device_proxy.b2CapabilityState = SPFCapabilityStates.OPERATE_FULL
    spfrx_device_proxy.b2CapabilityState = SPFRxCapabilityStates.CONFIGURE
    spfrx_events.wait_for_value(SPFRxCapabilityStates.CONFIGURE)
    spf_events.wait_for_value(SPFCapabilityStates.OPERATE_FULL)

    event_store.wait_for_value(CapabilityStates.CONFIGURING, timeout=8)
