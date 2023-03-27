"""Test StandbyLP"""
import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_standby_lp_transition(event_store_class, dish_manager_proxy):
    """Test transition to Standby_LP"""
    dish_mode_event_store = event_store_class()
    progress_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    dish_mode_event_store.clear_queue()
    progress_event_store.clear_queue()

    dish_manager_proxy.SetStandbyFPMode()
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=10)

    assert dish_manager_proxy.dishMode == DishMode.STANDBY_FP

    progress_event_store.clear_queue()

    dish_manager_proxy.SetStandbyLPMode()
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_LP, timeout=10)

    assert dish_manager_proxy.dishMode == DishMode.STANDBY_LP

    expected_progress_updates = [
        "SetStandbyLPMode called on DS",
        "SetStandbyLPMode called on SPF",
        "SetStandbyMode called on SPFRx",
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
