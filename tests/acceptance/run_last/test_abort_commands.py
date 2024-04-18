"""Test AbortCommands"""
import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode


@pytest.fixture(autouse=True)
def turn_on_spf_attribute_update(request, spf_device_proxy):
    """Ensure that attribute updates on spf is restored"""

    def toggle_attribute_update():
        spf_device_proxy.skipAttributeUpdates = False

    request.addfinalizer(toggle_attribute_update)


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_abort_commands(event_store_class, dish_manager_proxy, spf_device_proxy):
    """Test AbortCommands aborts the executing long running command"""
    # Set a flag on SPF to skip attribute updates
    # This is useful to ensure that the long running command
    # does not finish executing before AbortCommands is triggered
    dish_manager_proxy.SetStowMode()
    assert dish_manager_proxy.dishMode != DishMode.STOW

    spf_device_proxy.skipAttributeUpdates = True

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

    # Transition to FP mode
    [[_], [unique_id]] = dish_manager_proxy.SetStandbyFPMode()

    # Check that Dish Manager doesn't actually transition to FP
    progress_event_store.wait_for_progress_update("Awaiting dishMode change to STANDBY_FP")

    # Abort the LRC
    dish_manager_proxy.AbortCommands()

    # Confirm Dish Manager aborted the request on lRC
    result_event_store.wait_for_command_id(unique_id, timeout=5)
    progress_event_store.wait_for_progress_update("SetStandbyFPMode Aborted")

    # Check that the Dish Manager did not transition to FP
    assert dish_manager_proxy.dishMode != DishMode.STANDBY_FP

    # Ensure that the queue is cleared out
    cmds_in_queue_store.wait_for_value((), 10)
