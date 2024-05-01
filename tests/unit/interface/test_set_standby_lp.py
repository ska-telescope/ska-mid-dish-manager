"""Unit tests for setstandby_lp command."""

import pytest
import tango
from ska_control_model import ResultCode

from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    SPFOperatingMode,
    SPFRxOperatingMode,
)


# pylint:disable=protected-access
@pytest.mark.unit
@pytest.mark.forked
def test_standbylp_cmd_fails_from_standbylp_dish_mode(dish_manager_resources, event_store_class):
    """Execute tests"""
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


# pylint:disable=protected-access
@pytest.mark.unit
@pytest.mark.forked
def test_standbylp_cmd_succeeds_from_standbyfp_dish_mode(
    dish_manager_resources, event_store_class
):
    """Execute tests"""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]
    spfrx_cm = dish_manager_cm.sub_component_managers["SPFRX"]

    dish_mode_event_store = event_store_class()
    progress_event_store = event_store_class()

    device_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )

    device_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    assert dish_mode_event_store.wait_for_value(DishMode.STANDBY_LP)

    # Force dishManager dishMode to go to STANDBY-FP
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_FP)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.STANDBY)
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP)

    # Transition DishManager to STANDBY_LP issuing a command
    [[result_code], [_]] = device_proxy.SetStandbyLPMode()
    assert ResultCode(result_code) == ResultCode.QUEUED

    # Clear out the queue to make sure we don't catch old events
    dish_mode_event_store.clear_queue()

    # transition subservient devices to their respective operatingMode
    # and observe that DishManager transitions dishMode to LP mode. No
    # need to change the component state of SPFRX since it's in the
    # expected operating mode
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_LP)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.STANDBY_LP)

    # we can now expect dishMode to transition to STANDBY_LP
    assert dish_mode_event_store.wait_for_value(DishMode.STANDBY_LP, timeout=6)

    expected_progress_updates = [
        "SetStandbyLPMode called on DS",
        "SetStandbyLPMode called on SPF",
        "SetStandbyMode called on SPFRx",
        "Awaiting dishMode change to STANDBY_LP",
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
