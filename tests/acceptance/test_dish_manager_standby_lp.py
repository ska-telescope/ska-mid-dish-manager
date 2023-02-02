"""Test StandbyLP"""
import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_standby_lp_transition(event_store_class):
    """Test transition to Standby_LP"""
    dish_manager = tango.DeviceProxy("mid_d0001/elt/master")

    dish_mode_event_store = event_store_class()
    progress_event_store = event_store_class()

    dish_manager.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )

    dish_manager.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    dish_mode_event_store.clear_queue()
    progress_event_store.clear_queue()

    dish_manager.SetStandbyFPMode()
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=10)

    assert dish_manager.dishMode == DishMode.STANDBY_FP

    dish_manager.SetStandbyLPMode()
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_LP, timeout=10)

    assert dish_manager.dishMode == DishMode.STANDBY_LP

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
