"""Test StandbyLPMode unhappy path."""
import pytest
import tango
from ska_mid_dish_manager.models.dish_enums import DishMode


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_standbyfpmode_raise_exceptions(dish_manager_proxy,spf_device_proxy):
    """Tests if standbyLP command fails when an exception is raised."""

    result_event_store = event_store_class()
    # Tango Subscription to the dishMode attribute.
    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dishmode_event_store,
    )
    # Waiting for the dish mode to be Standby LP
    dishmode_event_store.wait_for_value(DishMode.STANDBY_LP)
    # Transition to STANDBY_FP and await the change to complete.
    dish_manager_proxy.SetStandbyFPMode()
    dishmode_event_store.wait_for_value(DishMode.STANDBY_FP)

    # Intentionally raising an exception on the SPF device.
    spf_device_proxy.raiseCmdException = True

    # Intitializing event store classes.
    result_event_store = event_store_class()
    status_event_store = event_store_class()

    # Tango Subscription to the LRC result.
    dish_manager_proxy.subscribe_event(
        "longrunningCommandprogress",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )

    # Tango Subscription to the LRC Status.
    dish_manager_proxy.subscribe_event(
        "longRunningCommandStatus",
        tango.EventType.CHANGE_EVENT,
        status_event_store,
    )

    # Transition to FP mode
    [[_], [unique_id]] = dish_manager_proxy.SetStandbyFPMode()
    status_events = status_event_store.wait_for_command_id(unique_id, timeout=8)

    expected_status = [f"{unique_id}_SetStandbyLPMode",'FAILED']
    
    # Waiting for the _SetStandbyLPMode to complete executing.
    progress_events = progress_event_store.wait_for_progress_update(
        "SetStandbyLPMode completed", timeout=6
    )

    # Join all the LRC status logs into one string.
    status_events_string = "".join([str(event) for event in status_events])

    # Check if a fail message is reported.
    for message in expected_status:
        assert message in status_events_string
