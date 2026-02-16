"""Test Operate."""

import pytest
from ska_mid_dish_utils.models.dish_enums import Band, DishMode

from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.mark.xfail(
    reason="operate mode event is intermittently not being emitted, needs investigation"
)
@pytest.mark.acceptance
def test_set_operate(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
):
    """Test transition to OPERATE."""
    main_event_store = event_store_class()
    band_event_store = event_store_class()
    status_event_store = event_store_class()
    attr_cb_mapping = {
        "dishMode": main_event_store,
        "configuredBand": band_event_store,
        "Status": status_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    dish_manager_proxy.ConfigureBand1(True)
    band_event_store.wait_for_value(Band.B1, timeout=30)

    # Await auto transition to OPERATE following band config
    main_event_store.wait_for_value(DishMode.OPERATE, timeout=30)

    expected_progress_updates = [
        "Fanned out commands: DS.SetIndexPosition, SPFRX.ConfigureBand1",
        "ConfigureBand1 complete. Triggering on success action.",
        "Fanned out commands: SPF.SetOperateMode, DS.SetPointMode",
        "Awaiting dishmode change to OPERATE",
        "SetOperateMode completed",
    ]

    events = status_event_store.wait_for_progress_update(expected_progress_updates[-1], timeout=6)

    events_string = "".join([str(event.attr_value.value) for event in events])

    for message in expected_progress_updates:
        assert message in events_string

    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
def test_set_operate_from_standbyfp(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
):
    """Test explicit transition to OPERATE from STANDBY_FP."""
    main_event_store = event_store_class()
    band_event_store = event_store_class()
    status_event_store = event_store_class()
    result_event_store = event_store_class()
    attr_cb_mapping = {
        "dishMode": main_event_store,
        "configuredBand": band_event_store,
        "Status": status_event_store,
        "longRunningCommandResult": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    # Configure a band
    dish_manager_proxy.ConfigureBand1(True)
    band_event_store.wait_for_value(Band.B1, timeout=30)
    # Await auto transition to OPERATE following band config
    main_event_store.wait_for_value(DishMode.OPERATE, timeout=30)

    # Transition to STANDBY_FP
    dish_manager_proxy.SetStandbyFPMode()
    main_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=30)

    # Test direct SetOperateMode command from STANDBY_FP
    [[_], [unique_id]] = dish_manager_proxy.SetOperateMode()
    result_event_store.wait_for_command_result(
        unique_id, '[0, "SetOperateMode completed"]', timeout=30
    )
    main_event_store.wait_for_value(DishMode.OPERATE, timeout=30)

    remove_subscriptions(subscriptions)
