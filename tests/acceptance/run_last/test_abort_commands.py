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
def test_abort_commands(event_store, event_store_class, dish_manager_proxy, spf_device_proxy):
    """Test AbortCommands aborts the executing long running command"""
    # Set a flag on SPF to skip attribute updates
    # This is useful to ensure that the long running command
    # does not finish executing before AbortCommands is triggered
    spf_device_proxy.skipAttributeUpdates = True

    # progress_event_store = event_store_class()
    # result_event_store = event_store_class()

    for attr in [
        "longRunningCommandResult",
        "longRunningCommandProgress",
    ]:
        dish_manager_proxy.subscribe_event(
            attr,
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

    cmds_in_queue_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        "longRunningCommandsInQueue",
        tango.EventType.CHANGE_EVENT,
        cmds_in_queue_store,
    )

    # Transition to FP mode
    [[_], [unique_id]] = dish_manager_proxy.SetStandbyFPMode()

    # Check that Dish Manager doesn't actually transition to FP
    event_store.wait_for_value((f"{unique_id}", "Awaiting dishMode change to STANDBY_FP"))

    # Abort the LRC
    dish_manager_proxy.AbortCommands()

    # Confirm Dish Manager aborted the request on lRC
    event_store.wait_for_command_id(unique_id, timeout=5)
    event_store.wait_for_value((f"{unique_id}", "SetStandbyFPMode Aborted"))

    # Check that the Dish Manager did not transition to FP
    assert dish_manager_proxy.dishMode != DishMode.STANDBY_FP

    # Get earlier queue values
    earlier_commands_in_queue = cmds_in_queue_store.get_queue_values()
    assert earlier_commands_in_queue

    # Ensure that the queue is cleared out
    cmds_in_queue_store.wait_for_value([], queue_event=True)
