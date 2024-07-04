"""Test ConfigureBand2"""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import Band, DishMode


# pylint: disable=too-many-locals,unused-argument,too-many-arguments
@pytest.mark.acceptance
@pytest.mark.forked
def test_configure_band_2(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
):
    """Test ConfigureBand2"""
    main_event_store = event_store_class()
    result_event_store = event_store_class()
    progress_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "longrunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    attributes = ["dishMode", "configuredBand"]
    for attribute_name in attributes:
        dish_manager_proxy.subscribe_event(
            attribute_name,
            tango.EventType.CHANGE_EVENT,
            main_event_store,
        )

    dish_manager_proxy.SetStandbyFPMode()
    main_event_store.wait_for_value(DishMode.STANDBY_FP)
    assert dish_manager_proxy.dishMode == DishMode.STANDBY_FP
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
    progress_event_store.wait_for_progress_update("Already in band 2")
    result_event_store.wait_for_command_result(unique_id, '[0, "ConfigureBand2 completed"]')
    assert dish_manager_proxy.configuredBand == Band.B2
