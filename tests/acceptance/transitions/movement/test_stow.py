"""Test that DS goes into STOW and dishManager reports it."""

import json

import pytest
from ska_control_model import ResultCode

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
    lrc_event_store = event_store_class()
    attr_cb_mapping = {
        "dishMode": main_event_store,
        "Status": status_event_store,
        "lrcFinished": lrc_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)
    expected_progress_update = "Stow called, monitor dishmode for LRC completed"

    if dish_manager_proxy.dishMode == DishMode.STOW:
        dish_manager_proxy.setstandbylpmode()
        main_event_store.wait_for_value(DishMode.STANDBY_LP, timeout=60)

    current_el = dish_manager_proxy.achievedPointing[2]
    stow_position = 90.2
    estimate_stow_duration = stow_position - current_el  # elevation speed is 1 degree per second

    lrc_event_store.clear_queue()
    [[result_code], [command_message]] = dish_manager_proxy.SetStowMode()

    assert ResultCode(result_code) == ResultCode.STARTED
    assert command_message == "Stow called on Dish Structure, monitor dishmode for STOW"

    [event] = lrc_event_store.wait_for_n_events(1, timeout=200)
    event_json = json.loads(event.attr_value.value[0])
    assert event_json["name"] == "SetStowMode"
    assert event_json["status"] == "COMPLETED"

    main_event_store.wait_for_value(DishMode.STOW, timeout=estimate_stow_duration + 60)

    events = status_event_store.wait_for_progress_update(expected_progress_update, timeout=10)
    assert events

    remove_subscriptions(subscriptions)
