"""Test ConfigureBand2."""

import pytest

from ska_mid_dish_manager.models.dish_enums import Band, DishMode
from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.mark.acceptance
@pytest.mark.forked
def test_configure_band_2(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
):
    """Test ConfigureBand2."""
    main_event_store = event_store_class()
    result_event_store = event_store_class()
    progress_event_store = event_store_class()

    attr_cb_mapping = {
        "dishMode": main_event_store,
        "configuredBand": main_event_store,
        "longRunningCommandProgress": progress_event_store,
        "longRunningCommandResult": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    # make sure configuredBand is not B2
    [[_], [unique_id]] = dish_manager_proxy.ConfigureBand1(True)
    result_event_store.wait_for_command_result(
        unique_id, '[0, "SetOperateMode completed"]', timeout=30
    )
    assert dish_manager_proxy.configuredBand == Band.B1
    assert dish_manager_proxy.dishMode == DishMode.OPERATE

    main_event_store.clear_queue()
    progress_event_store.clear_queue()

    [[_], [unique_id]] = dish_manager_proxy.ConfigureBand2(True)
    result_event_store.wait_for_command_result(
        unique_id, '[0, "SetOperateMode completed"]', timeout=30
    )
    main_event_store.wait_for_value(Band.B2, timeout=30)
    main_event_store.wait_for_value(DishMode.OPERATE, timeout=30)
    assert dish_manager_proxy.configuredBand == Band.B2
    assert dish_manager_proxy.dishMode == DishMode.OPERATE

    expected_progress_updates = [
        # ConfigureBand2
        "SetIndexPosition called on DS",
        "Awaiting DS indexerposition change to B2",
        "ConfigureBand2 called on SPFRX, ID",
        "Awaiting SPFRX configuredband change to B2",
        "Awaiting configuredband change to B2",
        "DS indexerposition changed to B2",
        "DS.SetIndexPosition completed",
        "SPFRX configuredband changed to B2",
        "SPFRX.ConfigureBand2 completed",
        "ConfigureBand2 complete. Triggering on success action.",
        # Then SetOperateMode
        "SetOperateMode called on SPF",
        "Awaiting SPF operatingmode change to OPERATE",
        "SetPointMode called on DS",
        "Awaiting DS operatingmode change to POINT",
        "Awaiting dishmode change to OPERATE",
        "SPF operatingmode changed to OPERATE",
        "SPF.SetOperateMode completed",
        "DS operatingmode changed to POINT",
        "DS.SetPointMode completed",
        "SetOperateMode completed",
    ]

    events = progress_event_store.get_queue_values(timeout=0)

    events_string = "".join([str(attr_value) for _, attr_value in events])
    for message in expected_progress_updates:
        assert message in events_string

    # Do it again to check result
    result_event_store.clear_queue()
    progress_event_store.clear_queue()

    [[_], [unique_id]] = dish_manager_proxy.ConfigureBand2(True)
    progress_event_store.wait_for_progress_update("Already in band 2", timeout=10)
    result_event_store.wait_for_command_result(
        unique_id, '[0, "ConfigureBand2 completed"]', timeout=10
    )
    assert dish_manager_proxy.configuredBand == Band.B2
    assert dish_manager_proxy.dishMode == DishMode.OPERATE

    remove_subscriptions(subscriptions)
