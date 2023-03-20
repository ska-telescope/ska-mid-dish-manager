"""Test StandbyFP"""
import pytest
import tango

from ska_mid_dish_manager.devices.test_devices.utils import (
    set_configuredBand_b1,
    set_configuredBand_b2,
)


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_standby_fp_transition(event_store_class):
    """Test transition to Standby_FP"""
    dish_manager = tango.DeviceProxy("ska001/elt/master")

    result_event_store = event_store_class()
    progress_event_store = event_store_class()

    dish_manager.subscribe_event(
        "longrunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )

    dish_manager.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    # Force a transition
    set_configuredBand_b1()
    set_configuredBand_b2()

    [[_], [unique_id]] = dish_manager.SetStandbyFPMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    expected_progress_updates = [
        "SetStandbyFPMode called on DS",
        "SetOperateMode called on SPF",
        "Awaiting dishMode change to STANDBY_FP",
        "SetStandbyFPMode completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string
