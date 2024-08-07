"""Test AbortCommands"""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode, DSOperatingMode, SPFOperatingMode


# pylint: disable=invalid-name, redefined-outer-name
@pytest.fixture
def toggle_skip_attributes(spf_device_proxy, dish_manager_proxy, event_store_class):
    """Ensure that attribute updates on spf is restored"""
    spf_device_proxy.skipAttributeUpdates = True
    yield
    # The test does not allow SPF to go to FP, while the others do.
    # We need to get it back to a consistent state
    spf_device_proxy.skipAttributeUpdates = False

    dish_mode_event_store = event_store_class()
    operating_mode_event_store = event_store_class()

    spf_device_proxy.subscribe_event(
        "operatingMode",
        tango.EventType.CHANGE_EVENT,
        operating_mode_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )

    spf_device_proxy.SetOperateMode()
    operating_mode_event_store.wait_for_value(SPFOperatingMode.OPERATE, timeout=10)
    # TODO DishManager does not react appropriately after it executes abort commands
    # Investigate if further action is required on dish manager's TaskExecutor after
    # abort is requested. DishMode reflects UNKNOWN not STANDBY_FP
    # dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=30)


# pylint: disable=unused-argument
@pytest.mark.acceptance
@pytest.mark.forked
def test_abort_commands(
    event_store_class,
    dish_manager_proxy,
    spf_device_proxy,
    ds_device_proxy,
    toggle_skip_attributes,
):
    """Test AbortCommands aborts the executing long running command"""
    # Set a flag on SPF to skip attribute updates.
    # This is useful to ensure that the long running command
    # does not finish executing before AbortCommands is triggered

    progress_event_store = event_store_class()
    result_event_store = event_store_class()
    cmds_in_queue_store = event_store_class()
    operating_mode_event_store = event_store_class()

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

    ds_device_proxy.subscribe_event(
        "operatingMode",
        tango.EventType.CHANGE_EVENT,
        operating_mode_event_store,
    )

    # Transition to FP mode
    [[_], [unique_id]] = dish_manager_proxy.SetStandbyFPMode()

    # wait for ds manager to finish its fanned out transition
    operating_mode_event_store.wait_for_value(DSOperatingMode.STANDBY_FP, timeout=10)

    # Check that Dish Manager doesn't actually transition to FP
    progress_event_store.wait_for_progress_update("Awaiting dishmode change to STANDBY_FP")

    # Abort the LRC
    dish_manager_proxy.AbortCommands()

    # Confirm Dish Manager aborted the request on lRC
    result_event_store.wait_for_command_id(unique_id)
    progress_event_store.wait_for_progress_update("SetStandbyFPMode Aborted")

    # Check that the Dish Manager did not transition to FP
    assert spf_device_proxy.operatingMode == SPFOperatingMode.STANDBY_LP
    assert ds_device_proxy.operatingMode == DSOperatingMode.STANDBY_FP
    assert dish_manager_proxy.dishMode != DishMode.STANDBY_FP

    # Ensure that the queue is cleared out
    cmds_in_queue_store.wait_for_value((), timeout=30)
