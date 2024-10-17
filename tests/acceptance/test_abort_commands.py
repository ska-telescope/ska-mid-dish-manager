"""Test AbortCommands"""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode, DSOperatingMode, SPFOperatingMode


@pytest.mark.acceptance
@pytest.mark.forked
def test_abort_commands(
    event_store_class,
    dish_manager_proxy,
    spf_device_proxy,
    ds_device_proxy,
):
    """Test AbortCommands aborts the executing long running command"""
    # Set a flag on SPF to skip attribute updates.
    # This is useful to ensure that the long running command
    # does not finish executing before AbortCommands is triggered
    spf_device_proxy.skipAttributeUpdates = True

    dish_mode_event_store = event_store_class()
    spf_operating_mode_event_store = event_store_class()
    progress_event_store = event_store_class()
    result_event_store = event_store_class()
    cmds_in_queue_store = event_store_class()
    ds_operating_mode_event_store = event_store_class()

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

    spf_device_proxy.subscribe_event(
        "operatingMode",
        tango.EventType.CHANGE_EVENT,
        spf_operating_mode_event_store,
    )

    ds_device_proxy.subscribe_event(
        "operatingMode",
        tango.EventType.CHANGE_EVENT,
        ds_operating_mode_event_store,
    )

    # Transition to FP mode
    [[_], [fp_unique_id]] = dish_manager_proxy.SetStandbyFPMode()

    # wait for ds manager to finish its fanned out transition
    ds_operating_mode_event_store.wait_for_value(DSOperatingMode.STANDBY_FP, timeout=10)

    # Check that Dish Manager is waiting to transition to FP
    progress_event_store.wait_for_progress_update("Awaiting dishmode change to STANDBY_FP")
    # Check that the Dish Manager did not transition to FP
    assert spf_device_proxy.operatingMode == SPFOperatingMode.STANDBY_LP
    assert ds_device_proxy.operatingMode == DSOperatingMode.STANDBY_FP
    assert dish_manager_proxy.dishMode != DishMode.STANDBY_FP

    # enable spf to send attribute updates
    spf_device_proxy.skipAttributeUpdates = False

    # Abort the LRC
    [[_], [abort_unique_id]] = dish_manager_proxy.AbortCommands()

    # Confirm Dish Manager aborted the request on lRC
    result_event_store.wait_for_command_id(fp_unique_id)
    progress_event_store.wait_for_progress_update("SetStandbyFPMode Aborted")

    # Confirm that abort finished and the queue is cleared
    result_event_store.wait_for_command_id(abort_unique_id)
    cmds_in_queue_store.wait_for_value((), timeout=30)

    # Check that the Dish Manager transitioned to FP as part of the Abort sequence
    spf_operating_mode_event_store.wait_for_value(SPFOperatingMode.OPERATE, timeout=10)
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=30)

    assert spf_device_proxy.operatingMode == SPFOperatingMode.OPERATE
    assert ds_device_proxy.operatingMode == DSOperatingMode.STANDBY_FP
    assert dish_manager_proxy.dishMode == DishMode.STANDBY_FP
