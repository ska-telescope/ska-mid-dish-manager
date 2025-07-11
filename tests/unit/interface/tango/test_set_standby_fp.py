"""Unit tests for setstandby_fp command."""

import pytest
import tango
from ska_control_model import AdminMode

from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    DSPowerState,
    PowerState,
    SPFOperatingMode,
    SPFPowerState,
)


@pytest.mark.unit
@pytest.mark.forked
def test_standby_fp_from_standby_lp(dish_manager_resources, event_store_class):
    """Execute tests."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]

    dish_mode_event_store = event_store_class()
    progress_event_store = event_store_class()
    power_state_event_store = event_store_class()

    device_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )

    device_proxy.subscribe_event(
        "powerState",
        tango.EventType.CHANGE_EVENT,
        power_state_event_store,
    )

    device_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    assert device_proxy.dishMode == DishMode.STANDBY_LP
    assert device_proxy.powerState == PowerState.LOW
    device_proxy.SetStandbyFPMode()
    # wait a bit before forcing the updates on the subcomponents
    dish_mode_event_store.get_queue_values()

    # transition subservient devices to FP mode and observe that
    # DishManager transitions dishMode to FP mode after all
    # subservient devices are in FP
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_FP)
    ds_cm._update_component_state(powerstate=DSPowerState.FULL_POWER)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    spf_cm._update_component_state(powerstate=SPFPowerState.FULL_POWER)
    #  we can now expect dishMode to transition to STANDBY_FP
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP)
    assert device_proxy.dishMode == DishMode.STANDBY_FP
    power_state_event_store.wait_for_value(PowerState.FULL)
    assert device_proxy.powerState == PowerState.FULL

    expected_progress_updates = [
        "SetStandbyFPMode called on DS",
        "SetOperateMode called on SPF",
        "Awaiting dishmode change to STANDBY_FP",
        "SetStandbyFPMode completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event.attr_value.value) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string


@pytest.mark.unit
@pytest.mark.forked
def test_standby_fp_from_maintenance(dish_manager_resources, event_store_class):
    """Execute tests."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]
    spfrx_cm = dish_manager_cm.sub_component_managers["SPFRX"]

    dish_mode_event_store = event_store_class()
    progress_event_store = event_store_class()
    power_state_event_store = event_store_class()

    device_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )

    device_proxy.subscribe_event(
        "powerState",
        tango.EventType.CHANGE_EVENT,
        power_state_event_store,
    )

    device_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    # Force Maintenance dishMode
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STOW)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.MAINTENANCE)
    spfrx_cm._update_component_state(adminmode=AdminMode.ENGINEERING)

    assert device_proxy.dishMode == DishMode.MAINTENANCE

    device_proxy.SetStandbyFPMode()
    # wait a bit before forcing the updates on the subcomponents
    dish_mode_event_store.get_queue_values()

    # transition subservient devices to FP mode and observe that
    # DishManager transitions dishMode to FP mode after all
    # subservient devices are in FP
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_FP)
    ds_cm._update_component_state(powerstate=DSPowerState.FULL_POWER)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    spf_cm._update_component_state(powerstate=SPFPowerState.FULL_POWER)
    #  we can now expect dishMode to transition to STANDBY_FP
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP)
    assert device_proxy.dishMode == DishMode.STANDBY_FP
    power_state_event_store.wait_for_value(PowerState.FULL)
    assert device_proxy.powerState == PowerState.FULL

    expected_progress_updates = [
        "SetStandbyFPMode called on DS",
        "SetOperateMode called on SPF",
        "SetStandbyMode called on SPFRX",
        "Awaiting dishmode change to STANDBY_FP",
        "SetStandbyFPMode completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event.attr_value.value) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string
