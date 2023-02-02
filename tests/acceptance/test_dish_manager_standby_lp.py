"""Test StandbyLP"""
import pytest
import tango

from ska_mid_dish_manager.devices.test_devices.utils import set_dish_manager_to_standby_lp


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_standby_lp_transition(event_store_class):
    """Test transition to Standby_LP"""
    dish_manager = tango.DeviceProxy("mid_d0001/elt/master")

    progress_event_store = event_store_class()

    dish_manager.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    progress_event_store.clear_queue()

    set_dish_manager_to_standby_lp(event_store_class(), dish_manager)

    expected_progress_updates = [
        "SetStandbyLPMode called on DS",
        "SetStandbyLPMode called on SPF",
        "SetStandbyMode called on SPFRX",
        "Awaiting dishMode change to STANDBY_LP",
        "SetStandbyLPMode completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string
