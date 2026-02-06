"""Test StandbyFP."""

import pytest

from ska_mid_dish_manager.models.dish_enums import DishMode, PowerState
from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.mark.slow
@pytest.mark.acceptance
def test_standby_fp_transition(monitor_tango_servers, event_store_class, dish_manager_proxy):
    """Test transition to Standby_FP."""
    result_event_store = event_store_class()
    status_event_store = event_store_class()
    dish_mode_event_store = event_store_class()
    attr_cb_mapping = {
        "longRunningCommandResult": result_event_store,
        "dishmode": dish_mode_event_store,
        "Status": status_event_store,
    }

    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    [[_], [unique_id]] = dish_manager_proxy.SetStandbyLPMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    dish_mode_event_store.clear_queue()
    status_event_store.clear_queue()

    [[_], [unique_id]] = dish_manager_proxy.SetStandbyFPMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    expected_progress_updates = [
        "Fanned out commands: DS.SetStandbyMode, DS.SetPowerMode",
        "Awaiting dishmode change to STANDBY_FP",
        "SetStandbyFPMode completed",
    ]

    events = status_event_store.wait_for_progress_update(expected_progress_updates[-1], timeout=6)

    events_string = "".join([str(event.attr_value.value) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string

    assert dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP)
    assert dish_manager_proxy.powerState == PowerState.FULL

    remove_subscriptions(subscriptions)
