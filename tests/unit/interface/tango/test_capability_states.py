"""CapabilityState checks."""

import pytest
import tango
from ska_mid_dish_utils.models.dish_enums import (
    CapabilityStates,
    DishMode,
    DSOperatingMode,
    IndexerPosition,
    SPFCapabilityStates,
    SPFRxCapabilityStates,
)


@pytest.mark.unit
@pytest.mark.forked
def test_capabilitystate_available(dish_manager_resources):
    """Test cap state present."""
    device_proxy, _ = dish_manager_resources
    attributes = device_proxy.get_attribute_list()
    for capability in ("b1", "b2", "b3", "b4", "b5a", "b5b"):
        state_name = f"{capability}CapabilityState"
        assert state_name in attributes
        assert device_proxy.read_attribute(state_name).value == CapabilityStates.UNKNOWN


@pytest.mark.unit
@pytest.mark.forked
def test_b1capabilitystate_change(
    dish_manager_resources,
    event_store_class,
):
    """Test b1CapabilityState."""
    device_proxy, dish_manager_cm = dish_manager_resources
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]
    spfrx_cm = dish_manager_cm.sub_component_managers["SPFRX"]

    event_store = event_store_class()

    device_proxy.subscribe_event(
        "b1CapabilityState",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    device_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    # Mimic capabilitystatechanges on sub devices
    assert device_proxy.dishMode == DishMode.STANDBY_LP
    spfrx_cm._update_component_state(b1capabilitystate=SPFRxCapabilityStates.STANDBY)
    spf_cm._update_component_state(b1capabilitystate=SPFCapabilityStates.STANDBY)

    event_store.wait_for_value(CapabilityStates.STANDBY, timeout=7)


@pytest.mark.unit
@pytest.mark.forked
def test_b2capabilitystate_change(
    dish_manager_resources,
    event_store_class,
):
    """Test b2CapabilityState."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]
    spfrx_cm = dish_manager_cm.sub_component_managers["SPFRX"]

    event_store = event_store_class()

    device_proxy.subscribe_event(
        "b2CapabilityState",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    # Mimic capabilitystatechanges on sub devices
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STARTUP)
    spf_cm._update_component_state(b2capabilitystate=SPFCapabilityStates.UNAVAILABLE)
    spfrx_cm._update_component_state(b2capabilitystate=SPFRxCapabilityStates.UNAVAILABLE)

    event_store.wait_for_value(CapabilityStates.UNAVAILABLE, timeout=7)


@pytest.mark.unit
@pytest.mark.forked
def test_b3capabilitystate_change(
    dish_manager_resources,
    event_store_class,
):
    """Test b3CapabilityState."""
    device_proxy, dish_manager_cm = dish_manager_resources
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]
    spfrx_cm = dish_manager_cm.sub_component_managers["SPFRX"]

    event_store = event_store_class()

    device_proxy.subscribe_event(
        "b3CapabilityState",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    # Mimic capabilitystatechanges on sub devices
    dish_manager_cm._update_component_state(dishmode=DishMode.STOW)
    spf_cm._update_component_state(b3capabilitystate=SPFCapabilityStates.OPERATE_FULL)
    spfrx_cm._update_component_state(b3capabilitystate=SPFRxCapabilityStates.OPERATE)

    event_store.wait_for_value(CapabilityStates.OPERATE_FULL, timeout=7)


@pytest.mark.unit
@pytest.mark.forked
def test_b4capabilitystate_change(
    dish_manager_resources,
    event_store_class,
):
    """Test b4CapabilityState."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]
    spfrx_cm = dish_manager_cm.sub_component_managers["SPFRX"]

    event_store = event_store_class()

    device_proxy.subscribe_event(
        "b4CapabilityState",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    # Mimic capabilitystatechanges on sub devices
    dish_manager_cm._update_component_state(dishmode=DishMode.CONFIG)
    ds_cm._update_component_state(indexerposition=IndexerPosition.MOVING)
    spf_cm._update_component_state(b4capabilitystate=SPFCapabilityStates.OPERATE_DEGRADED)
    spfrx_cm._update_component_state(b4capabilitystate=SPFRxCapabilityStates.CONFIGURE)

    event_store.wait_for_value(CapabilityStates.CONFIGURING, timeout=7)


@pytest.mark.unit
@pytest.mark.forked
def test_b5acapabilitystate_change(
    dish_manager_resources,
    event_store_class,
):
    """Test b5aCapabilityState."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]
    spfrx_cm = dish_manager_cm.sub_component_managers["SPFRX"]

    event_store = event_store_class()

    device_proxy.subscribe_event(
        "b5aCapabilityState",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    # Mimic capabilitystatechanges on sub devices
    ds_cm._update_component_state(
        indexerposition=IndexerPosition.B1,
        operatingmode=DSOperatingMode.STOW,
    )
    spf_cm._update_component_state(b5acapabilitystate=SPFCapabilityStates.OPERATE_DEGRADED)
    spfrx_cm._update_component_state(b5acapabilitystate=SPFRxCapabilityStates.OPERATE)

    event_store.wait_for_value(CapabilityStates.OPERATE_DEGRADED, timeout=7)


@pytest.mark.unit
@pytest.mark.forked
def test_b2capabilitystate_configuring_change(
    dish_manager_resources,
    event_store_class,
):
    """Test Configuring."""
    device_proxy, dish_manager_cm = dish_manager_resources
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]
    spfrx_cm = dish_manager_cm.sub_component_managers["SPFRX"]

    event_store = event_store_class()

    device_proxy.subscribe_event(
        "b2CapabilityState",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    # Mimic capabilitystatechanges on sub devices
    dish_manager_cm._update_component_state(dishmode=DishMode.CONFIG)
    spf_cm._update_component_state(b2capabilitystate=SPFCapabilityStates.OPERATE_FULL)
    spfrx_cm._update_component_state(b2capabilitystate=SPFRxCapabilityStates.CONFIGURE)

    event_store.wait_for_value(CapabilityStates.CONFIGURING, timeout=7)
