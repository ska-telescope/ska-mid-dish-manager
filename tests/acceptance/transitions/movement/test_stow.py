"""Test that DS goes into STOW and dishManager reports it."""

import pytest

from ska_mid_dish_manager.models.dish_enums import DishMode
from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.mark.movement
@pytest.mark.acceptance
def test_stow_transition(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
):
    """Test transition to STOW."""
    main_event_store = event_store_class()
    status_event_store = event_store_class()
    attr_cb_mapping = {
        "dishMode": main_event_store,
        "Status": status_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    current_el = dish_manager_proxy.achievedPointing[2]
    stow_position = 90.2
    estimate_stow_duration = stow_position - current_el  # elevation speed is 1 degree per second
    dish_manager_proxy.SetStowMode()
    main_event_store.wait_for_value(DishMode.STOW, timeout=estimate_stow_duration + 10)

    expected_progress_update = "Stow called, monitor dishmode for LRC completed"
    events = status_event_store.wait_for_progress_update(expected_progress_update)

    events_string = "".join([str(event.attr_value.value) for event in events])
    for message in expected_progress_update:
        assert message in events_string

    remove_subscriptions(subscriptions)
