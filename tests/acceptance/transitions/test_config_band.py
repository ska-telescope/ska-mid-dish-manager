"""Test ConfigureBand2."""

import pytest

from ska_mid_dish_manager.models.dish_enums import Band
from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.mark.acceptance
def test_configure_band_a(monitor_tango_servers, event_store_class, dish_manager_proxy):
    """Test ConfigureBand2."""
    main_event_store = event_store_class()
    result_event_store = event_store_class()
    status_event_store = event_store_class()

    attr_cb_mapping = {
        "configuredBand": main_event_store,
        "Status": status_event_store,
        "longRunningCommandResult": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    # make sure configuredBand is not B2
    if dish_manager_proxy.configuredBand != Band.B1:
        dish_manager_proxy.ConfigureBand1(True)
        main_event_store.wait_for_value(Band.B1, timeout=8)
        assert dish_manager_proxy.configuredBand == Band.B1

    main_event_store.clear_queue()
    status_event_store.clear_queue()

    dish_manager_proxy.ConfigureBand2(True)
    main_event_store.wait_for_value(Band.B2)
    assert dish_manager_proxy.configuredBand == Band.B2

    expected_progress_updates = [
        "Fanned out commands: DS.SetIndexPosition, SPFRX.ConfigureBand2",
        "Awaiting configuredband change to B2",
        "ConfigureBand2 completed",
    ]

    events = status_event_store.get_queue_values()

    events_string = "".join([str(event.attr_value.value) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store.
    for message in expected_progress_updates:
        assert message in events_string

    # Do it again to check result
    result_event_store.clear_queue()
    status_event_store.clear_queue()

    [[_], [unique_id]] = dish_manager_proxy.ConfigureBand2(True)
    status_event_store.wait_for_progress_update("Already in band 2", timeout=10)
    result_event_store.wait_for_command_result(
        unique_id, '[0, "ConfigureBand2 completed"]', timeout=10
    )
    assert dish_manager_proxy.configuredBand == Band.B2

    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
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
    status_event_store = event_store_class()

    attr_cb_mapping = {
        "configuredBand": main_event_store,
        "Status": status_event_store,
        "longRunningCommandResult": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    main_event_store.clear_queue()
    status_event_store.clear_queue()

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

    events = status_event_store.wait_for_progress_update(expected_progress_updates[-1], timeout=6)

    events_string = "".join([str(event.attr_value.value) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store.
    for message in expected_progress_updates:
        assert message in events_string

    # Do it again to check result
    result_event_store.clear_queue()
    status_event_store.clear_queue()

    remove_subscriptions(subscriptions)
