"""Unit tests for Abort/AbortCommands command."""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    PointingState,
    SPFOperatingMode,
)


# pylint:disable=protected-access
@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "abort_cmd, pointing_state",
    [
        ("Abort", PointingState.SLEW),
        ("AbortCommands", PointingState.TRACK),
    ],
)
def test_abort(dish_manager_resources, event_store_class, abort_cmd, pointing_state):
    """Verify Abort/AbortCommands executes the abort sequence"""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]

    dish_mode_event_store = event_store_class()
    progress_event_store = event_store_class()
    result_event_store = event_store_class()
    cmds_in_queue_store = event_store_class()

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

    device_proxy.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )

    device_proxy.subscribe_event(
        "longRunningCommandsInQueue",
        tango.EventType.CHANGE_EVENT,
        cmds_in_queue_store,
    )
    # since we check that the queue is empty, remove the empty queue
    # event received after subscription to prevent false reporting
    cmds_in_queue_store.clear_queue()

    # it doesnt matter which command is executed, so long as it's not STOW
    [[_], [fp_unique_id]] = device_proxy.SetStandbyFPMode()
    # dont update spf operatingMode to mimic skipAttributeUpdate=True
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_FP)
    # we can now expect dishMode to transition to UNKNOWN
    dish_mode_event_store.wait_for_value(DishMode.UNKNOWN)
    assert device_proxy.dishMode == DishMode.UNKNOWN
    # remove the progress events emitted from SetStandbyFPMode execution
    progress_event_store.clear_queue()

    # update the pointingState to simulate a dish movement
    ds_cm._update_component_state(pointingstate=pointing_state)

    # Abort the LRC
    [[_], [abort_unique_id]] = device_proxy.command_inout(abort_cmd, None)
    result_event_store.wait_for_command_id(fp_unique_id, timeout=30)
    progress_event_store.wait_for_progress_update("SetStandbyFPMode Aborted")

    progress_event_store.wait_for_progress_update("TrackStop called on DS", timeout=30)
    # update the pointingState to READY indicating dish movement finished
    ds_cm._update_component_state(pointingstate=PointingState.READY)
    expected_progress_updates = [
        "TrackStop completed",
        "Clearing scanID",
        "EndScan completed",
        "SetOperateMode called on SPF",
        "SetStandbyFPMode called on DS",
        "Awaiting dishmode change to STANDBY_FP",
    ]
    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=30
    )
    events_string = "".join([str(event.attr_value.value) for event in events])
    for message in expected_progress_updates:
        assert message in events_string

    # trigger update on spf to make sure FP transition happens
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    progress_event_store.wait_for_progress_update("SetStandbyFPMode completed", timeout=30)

    # Confirm that abort finished and the queue is cleared
    result_event_store.wait_for_command_id(abort_unique_id)
    cmds_in_queue_store.wait_for_value((), timeout=30)
    assert device_proxy.dishMode == DishMode.STANDBY_FP
