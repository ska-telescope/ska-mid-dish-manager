"""Test StandbyFPMode unhappy path."""
import pytest
import tango


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_standbyfpmode_raise_exceptions(event_store_class, dish_manager_proxy, spf_device_proxy):
    """Tests if standbyFP command fails when an exception is raised."""

    # Intentionally raising an exception on the SPF device.
    spf_device_proxy.raiseCmdException = True

    # Intitializing event store classes.
    progress_event_store = event_store_class()
    status_event_store = event_store_class()

    # Tango Subscription to the LRC progress.
    dish_manager_proxy.subscribe_event(
        "longrunningCommandprogress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
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

    expected_status = [f"{unique_id}_SetStandbyFPMode", "FAILED"]

    # Waiting for the _SetStandbyFPMode to complete executing.
    _ = progress_event_store.wait_for_progress_update("SetStandbyFPMode completed", timeout=6)

    # Join all the LRC status logs into one string.
    status_events_string = "".join([str(event) for event in status_events])

    # Check if a fail message is reported.
    for message in expected_status:
        assert message in status_events_string
