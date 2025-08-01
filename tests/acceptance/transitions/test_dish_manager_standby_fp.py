"""Test StandbyFP."""

import pytest

from ska_mid_dish_manager.models.dish_enums import DishMode, PowerState
from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.mark.acceptance
@pytest.mark.forked
def test_standby_fp_transition(monitor_tango_servers, event_store_class, dish_manager_proxy):
    """Test transition to Standby_FP."""
    result_event_store = event_store_class()
    progress_event_store = event_store_class()
    attr_cb_mapping = {
        "longRunningCommandProgress": progress_event_store,
        "longRunningCommandResult": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    [[_], [unique_id]] = dish_manager_proxy.SetStandbyLPMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    [[_], [unique_id]] = dish_manager_proxy.SetStandbyFPMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    expected_progress_updates = [
        "SetStandbyFPMode called on DS",
        "SetOperateMode called on SPF",
        "Awaiting dishmode change to STANDBY_FP",
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

    assert dish_manager_proxy.dishMode == DishMode.STANDBY_FP
    assert dish_manager_proxy.powerState == PowerState.FULL

    remove_subscriptions(subscriptions)
