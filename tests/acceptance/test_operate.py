"""Test Operate."""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import Band, DishMode


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

    for attr in [
        "dishMode",
        "longRunningCommandResult",
    ]:
        dish_manager_proxy.subscribe_event(
            attr,
            tango.EventType.CHANGE_EVENT,
            main_event_store,
        )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "configuredBand",
        tango.EventType.CHANGE_EVENT,
        band_event_store,
    )

    [[_], [unique_id]] = dish_manager_proxy.SetStandbyFPMode()
    main_event_store.wait_for_command_id(unique_id, timeout=8)
    assert dish_manager_proxy.dishMode == DishMode.STANDBY_FP

    dish_manager_proxy.ConfigureBand1(True)
    band_event_store.wait_for_value(Band.B1, timeout=8)

    dish_manager_proxy.SetOperateMode()
    main_event_store.wait_for_value(DishMode.OPERATE)
    assert dish_manager_proxy.dishMode == DishMode.OPERATE

    expected_progress_updates = [
        "SetPointMode called on DS",
        "SetOperateMode called on SPF",
        "Awaiting dishmode change to OPERATE",
        "SetOperateMode completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event) for event in events])

    for message in expected_progress_updates:
        assert message in events_string
