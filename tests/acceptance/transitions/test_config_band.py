"""Test ConfigureBand2."""

import json

import pytest

from ska_mid_dish_manager.models.dish_enums import Band
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
        "configuredBand": main_event_store,
        "longRunningCommandProgress": progress_event_store,
        "longRunningCommandResult": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    # make sure configuredBand is not B2
    dish_manager_proxy.ConfigureBand1(True)
    main_event_store.wait_for_value(Band.B1, timeout=8)
    assert dish_manager_proxy.configuredBand == Band.B1

    main_event_store.clear_queue()
    progress_event_store.clear_queue()

    dish_manager_proxy.ConfigureBand2(True)
    main_event_store.wait_for_value(Band.B2)
    assert dish_manager_proxy.configuredBand == Band.B2

    expected_progress_updates = [
        "SetIndexPosition called on DS",
        "ConfigureBand2 called on SPFRX, ID",
        "Awaiting configuredband change to B2",
        "ConfigureBand2 completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store.
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

    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.xfail(reason="Pending changes on simulator to exposeConfigureBand command on SPFRx")
def test_configure_band_2_json(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
):
    """Test ConfigureBand with JSON string."""
    main_event_store = event_store_class()
    result_event_store = event_store_class()
    progress_event_store = event_store_class()

    attr_cb_mapping = {
        "configuredBand": main_event_store,
        "longRunningCommandProgress": progress_event_store,
        "longRunningCommandResult": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    payload = {
        "receiver_band": "1",
        "spfrx_processing_parameters": {"dishes": ["all"], "sync_pps": True},
    }
    b1_data = json.dumps(payload, indent=4)
    # make sure configuredBand is not B2
    dish_manager_proxy.ConfigureBand(b1_data)
    main_event_store.wait_for_value(Band.B1, timeout=8)
    assert dish_manager_proxy.configuredBand == Band.B1

    main_event_store.clear_queue()
    progress_event_store.clear_queue()

    payload = {
        "receiver_band": "2",
        "spfrx_processing_parameters": {"dishes": ["all"], "sync_pps": True},
    }
    b2_data = json.dumps(payload, indent=4)
    dish_manager_proxy.ConfigureBand(b2_data)
    main_event_store.wait_for_value(Band.B2, timeout=8)
    assert dish_manager_proxy.configuredBand == Band.B2

    expected_progress_updates = [
        "SetIndexPosition called on DS",
        "ConfigureBand called on SPFRX, ID",
        "Awaiting configuredband change to B2",
        "ConfigureBand completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store.
    for message in expected_progress_updates:
        assert message in events_string

    # Do it again to check result
    result_event_store.clear_queue()
    progress_event_store.clear_queue()

    [[_], [unique_id]] = dish_manager_proxy.ConfigureBand(b2_data)
    progress_event_store.wait_for_progress_update("Already in band 2", timeout=10)
    result_event_store.wait_for_command_result(
        unique_id, '[0, "ConfigureBand completed"]', timeout=10
    )
    assert dish_manager_proxy.configuredBand == Band.B2

    remove_subscriptions(subscriptions)
