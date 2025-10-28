"""Test ConfigureBand2."""

import pytest

from ska_mid_dish_manager.models.dish_enums import Band
from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.mark.acceptance
@pytest.mark.forked
def test_configure_band_a(
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
    if dish_manager_proxy.configuredBand != Band.B1:
        dish_manager_proxy.ConfigureBand1(True)
        main_event_store.wait_for_value(Band.B1, timeout=8)
        assert dish_manager_proxy.configuredBand == Band.B1

    main_event_store.clear_queue()
    progress_event_store.clear_queue()

    dish_manager_proxy.ConfigureBand2(True)
    main_event_store.wait_for_value(Band.B2)
    assert dish_manager_proxy.configuredBand == Band.B2

    expected_progress_updates = [
        "Fanned out commands: DS.SetIndexPosition, SPFRX.ConfigureBand2",
        "Awaiting configuredband change to B2",
        "ConfigureBand2 completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event.attr_value.value) for event in events])

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

    json_payload_1 = """
    {
        "dish": {
            "receiver_band": "1",
            "spfrx_processing_parameters": [
                {
                    "dishes": ["all"],
                    "sync_pps": true
                }
            ]
        }
    }
    """
    # make sure configuredBand is not B2
    dish_manager_proxy.ConfigureBand(json_payload_1)
    main_event_store.wait_for_value(Band.B1, timeout=8)
    assert dish_manager_proxy.configuredBand == Band.B1

    progress_event_store.wait_for_progress_update("ConfigureBand completed")

    main_event_store.clear_queue()
    progress_event_store.clear_queue()

    json_payload_2 = """
    {
        "dish": {
            "receiver_band": "2",
            "spfrx_processing_parameters": [
                {
                    "dishes": ["all"],
                    "sync_pps": true
                }
            ]
        }
    }
    """
    dish_manager_proxy.ConfigureBand(json_payload_2)
    main_event_store.wait_for_value(Band.B2, timeout=8)
    assert dish_manager_proxy.configuredBand == Band.B2

    expected_progress_updates = [
        "Fanned out commands: DS.SetIndexPosition, SPFRX.ConfigureBand",
        "Awaiting configuredband change to B2",
        "SPFRX configuredband changed to B2",
        "DS indexerposition changed to B2",
        "ConfigureBand completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=10
    )

    # Do it again to check result
    result_event_store.clear_queue()
    progress_event_store.clear_queue()

    events_string = "".join([str(event.attr_value.value) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store.
    for message in expected_progress_updates:
        assert message in events_string

    [[_], [unique_id]] = dish_manager_proxy.ConfigureBand(json_payload_2)
    progress_event_store.wait_for_progress_update("Already in band B2", timeout=10)
    result_event_store.wait_for_command_result(
        unique_id, '[0, "ConfigureBand completed."]', timeout=10
    )
    assert dish_manager_proxy.configuredBand == Band.B2

    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
@pytest.mark.forked
def test_configure_band_5b_json(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
):
    """Test ConfigureBand with JSON string for configure band 5."""
    main_event_store = event_store_class()
    result_event_store = event_store_class()
    progress_event_store = event_store_class()

    attr_cb_mapping = {
        "configuredBand": main_event_store,
        "longRunningCommandProgress": progress_event_store,
        "longRunningCommandResult": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    json_payload = """
    {
        "dish": {
            "receiver_band": "5b",
            "sub_band": 1,
            "spfrx_processing_parameters": [
                {
                    "dishes": ["all"],
                    "sync_pps": true
                }
            ]
        }
    }
    """
    # make sure configuredBand is not B5b
    dish_manager_proxy.ConfigureBand(json_payload)
    main_event_store.wait_for_value(Band.B1, timeout=8)
    assert dish_manager_proxy.configuredBand == Band.B1

    expected_progress_updates = [
        "Fanned out commands: DS.SetIndexPosition, SPFRX.ConfigureBand",
        "Awaiting configuredband change to B1",
        "SPFRX configuredband changed to B1",
        "DS indexerposition changed to B1",
        "ConfigureBand completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=10
    )

    events_string = "".join([str(event.attr_value.value) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store.
    for message in expected_progress_updates:
        assert message in events_string

    remove_subscriptions(subscriptions)

@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.parametrize(
    ("band_request", "expected_band", "message_str"),
    [
        ("ConfigureBand1", Band.B1, "B1"),
        ("ConfigureBand3", Band.B3, "B3"),
        ("ConfigureBand4", Band.B4, "B4"),
        ("ConfigureBand5a", Band.B5a, "B5a"),
        # Special case for 5b until we have a B5DC
        ("ConfigureBand5b", Band.B1, "B1"),
        # End up in B2 again
        ("ConfigureBand2", Band.B2, "B2"),
    ],
)
def test_configure_band_b(
    band_request: str,
    expected_band: Band,
    message_str: str,
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
):
    """Test ConfigureBand."""
    # Just skip the band we already are in
    if expected_band == dish_manager_proxy.configuredBand:
        return

    main_event_store = event_store_class()
    result_event_store = event_store_class()
    progress_event_store = event_store_class()

    attr_cb_mapping = {
        "configuredBand": main_event_store,
        "longRunningCommandProgress": progress_event_store,
        "longRunningCommandResult": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    main_event_store.clear_queue()
    progress_event_store.clear_queue()

    res = dish_manager_proxy.command_inout(band_request, True)
    assert res
    assert len(res) == 2
    main_event_store.wait_for_value(expected_band, timeout=15)
    assert dish_manager_proxy.configuredBand == expected_band

    if band_request == "ConfigureBand5b":
        expected_progress_updates = [
            "Fanned out commands: DS.SetIndexPosition, SPFRX.ConfigureBand1",
            "Awaiting configuredband change to B1",
            "ConfigureBand1 completed",
        ]
    else:
        expected_progress_updates = [
            f"Fanned out commands: DS.SetIndexPosition, SPFRX.{band_request}",
            f"Awaiting configuredband change to {message_str}",
            f"{band_request} completed",
        ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event.attr_value.value) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store.
    for message in expected_progress_updates:
        assert message in events_string

    # Do it again to check result
    result_event_store.clear_queue()
    progress_event_store.clear_queue()

    remove_subscriptions(subscriptions)

