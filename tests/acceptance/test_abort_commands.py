"""Test AbortCommands"""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode


@pytest.mark.acceptance
@pytest.mark.forked
def test_abort_commands(
    event_store_class,
    dish_manager_proxy,
    spf_device_proxy,
):
    """Test AbortCommands aborts the executing long running command"""
    # Set a flag on SPF to skip attribute updates.
    # This is useful to ensure that the long running command
    # does not finish executing before AbortCommands is triggered
    spf_device_proxy.skipAttributeUpdates = True

    dish_mode_event_store = event_store_class()
    progress_event_store = event_store_class()
    result_event_store = event_store_class()
    cmds_in_queue_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandsInQueue",
        tango.EventType.CHANGE_EVENT,
        cmds_in_queue_store,
    )

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )

    # Transition to FP mode
    [[_], [fp_unique_id]] = dish_manager_proxy.SetStandbyFPMode()

    # Check that Dish Manager is waiting to transition to FP
    progress_event_store.wait_for_progress_update("Awaiting dishmode change to STANDBY_FP")
    # Check that the Dish Manager did not transition to FP
    assert dish_manager_proxy.dishMode == DishMode.UNKNOWN

    # enable spf to send attribute updates
    spf_device_proxy.skipAttributeUpdates = False

    # Abort the LRC
    [[_], [abort_unique_id]] = dish_manager_proxy.AbortCommands()
    # Confirm Dish Manager aborted the request on LRC
    result_event_store.wait_for_command_id(fp_unique_id, timeout=30)
    # Abort will execute standbyfp dishmode as part of its abort sequence
    expected_progress_updates = [
        "SetStandbyFPMode Aborted",
        "SetOperateMode called on SPF",
        "SetStandbyFPMode called on DS",
        "Awaiting dishmode change to STANDBY_FP",
        "SetStandbyFPMode completed",
    ]
    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )
    events_string = "".join([str(event.attr_value.value) for event in events])
    # Check that all the expected progress messages appeared
    for message in expected_progress_updates:
        assert message in events_string

    # Confirm that abort finished and the queue is cleared
    result_event_store.wait_for_command_id(abort_unique_id)
    cmds_in_queue_store.wait_for_value((), timeout=30)

    # Check that the Dish Manager transitioned to FP as part of the Abort sequence
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=30)
    assert dish_manager_proxy.dishMode == DishMode.STANDBY_FP
