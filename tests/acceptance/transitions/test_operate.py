"""Test Operate."""

import pytest

from ska_mid_dish_manager.models.dish_enums import Band, DishMode
from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.mark.acceptance
@pytest.mark.forked
def test_set_operate(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
):
    """Test transition to OPERATE."""
    main_event_store = event_store_class()
    band_event_store = event_store_class()
    progress_event_store = event_store_class()
    attr_cb_mapping = {
        "dishMode": main_event_store,
        "longRunningCommandProgress": progress_event_store,
        "longRunningCommandResult": main_event_store,
        "configuredBand": band_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    dish_manager_proxy.ConfigureBand1(True)
    band_event_store.wait_for_value(Band.B1, timeout=8)

    dish_manager_proxy.SetOperateMode()
    main_event_store.wait_for_value(DishMode.OPERATE, timeout=8)
    assert dish_manager_proxy.dishMode == DishMode.OPERATE

    expected_progress_updates = [
        "Fanned out commands: SPF.SetOperateMode, DS.SetPointMode",
        "Awaiting dishmode change to OPERATE",
        "SetOperateMode completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=30
    )

    events_string = "".join([str(event.attr_value.value) for event in events])

    for message in expected_progress_updates:
        assert message in events_string

    remove_subscriptions(subscriptions)
