"""Test StandbyLP."""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode, PowerState


@pytest.mark.acceptance
@pytest.mark.forked
def test_standby_lp_transition(monitor_tango_servers, event_store_class, dish_manager_proxy):
    """Test transition to Standby_LP."""
    progress_event_store = event_store_class()

    sub_id = dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    progress_event_store.clear_queue()
    dish_manager_proxy.SetStandbyLPMode()

    expected_progress_updates = [
        "Fanned out commands: SPF.SetStandbyLPMode, SPFRX.SetStandbyMode, DS.SetStandbyLPMode",
        "Awaiting dishmode change to STANDBY_LP",
        "SetStandbyLPMode completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=30
    )

    events_string = "".join([str(event.attr_value.value) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string

    assert dish_manager_proxy.dishMode == DishMode.STANDBY_LP
    assert dish_manager_proxy.powerState == PowerState.LOW

    dish_manager_proxy.unsubscribe_event(sub_id)
