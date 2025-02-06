"""Test that DS goes into STOW and dishManager reports it"""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode


# pylint: disable=too-many-locals,unused-argument
@pytest.mark.acceptance
@pytest.mark.forked
def test_stow_transition(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
):
    """Test transition to STOW"""
    main_event_store = event_store_class()
    progress_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    current_el = dish_manager_proxy.achievedPointing[2]
    stow_position = 90.2
    estimate_stow_duration = stow_position - current_el  # elevation speed is 1 degree per second
    dish_manager_proxy.SetStowMode()
    main_event_store.wait_for_value(DishMode.STOW, timeout=estimate_stow_duration + 10)

    expected_progress_update = "Stow called, monitor dishmode for LRC completed"
    events = progress_event_store.wait_for_progress_update(expected_progress_update)

    events_string = "".join([str(event) for event in events])
    for message in expected_progress_update:
        assert message in events_string
