"""Test StandbyLP."""

import pytest

from ska_mid_dish_manager.models.dish_enums import DishMode, PowerState
from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.mark.acceptance
@pytest.mark.forked
def test_standby_lp_transition(monitor_tango_servers, event_store_class, dish_manager_proxy):
    """Test transition to Standby_LP."""
    progress_event_store = event_store_class()
    main_event_store = event_store_class()
    attr_cb_mapping = {
        "longRunningCommandProgress": progress_event_store,
        "dishmode": main_event_store,
        "powerstate": main_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    progress_event_store.clear_queue()
    dish_manager_proxy.SetStandbyLPMode()

    expected_progress_updates = [
        "SetStandbyMode called on DS",
        "SetStandbyLPMode called on SPF",
        "SetStandbyMode called on SPFRX",
        "Awaiting dishmode change to STANDBY_LP",
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

    main_event_store.wait_for_value(DishMode.STANDBY_LP)
    assert dish_manager_proxy.powerState == PowerState.LOW

    remove_subscriptions(subscriptions)
