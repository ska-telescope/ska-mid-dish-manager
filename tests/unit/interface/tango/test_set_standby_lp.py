"""Unit tests for setstandby_lp command."""

import pytest
import tango
from ska_control_model import AdminMode, ResultCode

from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    DSPowerState,
    PowerState,
    SPFOperatingMode,
    SPFPowerState,
    SPFRxOperatingMode,
)


@pytest.mark.unit
@pytest.mark.forked
def test_standbylp_cmd_fails_from_standbylp_dish_mode(dish_manager_resources, event_store_class):
    """Execute tests."""
    device_proxy, _ = dish_manager_resources

    dish_mode_event_store = event_store_class()
    lrc_status_event_store = event_store_class()

    device_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )

    device_proxy.subscribe_event(
        "longRunningCommandStatus",
        tango.EventType.CHANGE_EVENT,
        lrc_status_event_store,
    )

    dish_mode_event_store.wait_for_value(DishMode.STANDBY_LP)

    [[_], [unique_id]] = device_proxy.SetStandbyLPMode()
    lrc_status_event_store.wait_for_value((unique_id, "REJECTED"))


@pytest.mark.unit
@pytest.mark.forked
def test_standbylp_cmd_succeeds_from_standbyfp_dish_mode(
    dish_manager_resources, event_store_class
):
    """Execute tests."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]
    spfrx_cm = dish_manager_cm.sub_component_managers["SPFRX"]

    dish_mode_event_store = event_store_class()
    power_state_event_store = event_store_class()
    progress_event_store = event_store_class()

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
    # Force dishManager dishMode to go to STANDBY-FP
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_FP)
    ds_cm._update_component_state(powerstate=DSPowerState.FULL_POWER)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    spf_cm._update_component_state(powerstate=SPFPowerState.FULL_POWER)
    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.STANDBY)

    dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP)
    assert device_proxy.dishMode == DishMode.STANDBY_FP
    power_state_event_store.wait_for_value(PowerState.FULL)
    assert device_proxy.powerState == PowerState.FULL

    # Transition DishManager to STANDBY_LP issuing a command
    [[result_code], [_]] = device_proxy.SetStandbyLPMode()
    assert ResultCode(result_code) == ResultCode.QUEUED
    # wait a bit before forcing the updates on the subcomponents
    # this will also clear the queue of any existing events
    dish_mode_event_store.get_queue_values()

    # transition subservient devices to their respective operatingMode
    # and observe that DishManager transitions dishMode to LP mode. No
    # need to change the component state of SPFRX since it's in the
    # expected operating mode
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_LP)
    ds_cm._update_component_state(powerstate=DSPowerState.LOW_POWER)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.STANDBY_LP)
    spf_cm._update_component_state(powerstate=SPFPowerState.LOW_POWER)

    # we can now expect dishMode to transition to STANDBY_LP and powerState to LOW
    assert dish_mode_event_store.wait_for_value(DishMode.STANDBY_LP)
    assert device_proxy.dishMode == DishMode.STANDBY_LP
    assert power_state_event_store.wait_for_value(PowerState.LOW)
    assert device_proxy.powerState == PowerState.LOW

    expected_progress_updates = [
        "Fanned out commands: SPF.SetStandbyLPMode, SPFRX.SetStandbyMode, DS.SetStandbyLPMode",
        "Awaiting dishmode change to STANDBY_LP",
        "SetStandbyLPMode completed",
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
def test_standbylp_cmd_succeeds_from_maintenance_dish_mode(
    dish_manager_resources, event_store_class
):
    """Execute tests."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]
    spfrx_cm = dish_manager_cm.sub_component_managers["SPFRX"]

    dish_mode_event_store = event_store_class()
    power_state_event_store = event_store_class()
    progress_event_store = event_store_class()

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

    # Force dishManager dishMode to go to MAINTENANCE
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STOW)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.MAINTENANCE)
    spfrx_cm._update_component_state(adminmode=AdminMode.ENGINEERING)

    dish_mode_event_store.wait_for_value(DishMode.MAINTENANCE)
    assert device_proxy.dishMode == DishMode.MAINTENANCE

    # Transition DishManager to STANDBY_LP issuing a command
    [[result_code], [_]] = device_proxy.SetStandbyLPMode()
    assert ResultCode(result_code) == ResultCode.QUEUED
    # wait a bit before forcing the updates on the subcomponents
    # this will also clear the queue of any existing events
    dish_mode_event_store.get_queue_values()

    # transition subservient devices to their respective operatingMode
    # and observe that DishManager transitions dishMode to LP mode.
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_LP)
    ds_cm._update_component_state(powerstate=DSPowerState.LOW_POWER)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.STANDBY_LP)
    spf_cm._update_component_state(powerstate=SPFPowerState.LOW_POWER)
    spfrx_cm._update_component_state(adminmode=AdminMode.ONLINE)

    # we can now expect dishMode to transition to STANDBY_LP and powerState to LOW
    assert dish_mode_event_store.wait_for_value(DishMode.STANDBY_LP)
    assert device_proxy.dishMode == DishMode.STANDBY_LP
    assert power_state_event_store.wait_for_value(PowerState.LOW)
    assert device_proxy.powerState == PowerState.LOW

    expected_progress_updates = [
        "Fanned out commands: SPF.SetStandbyLPMode, SPFRX.SetStandbyMode, DS.SetStandbyLPMode",
        "Awaiting dishmode change to STANDBY_LP",
        "SetStandbyLPMode completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event.attr_value.value) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string
