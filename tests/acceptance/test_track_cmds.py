"""Test that DS goes into Track and dishManager reports it"""
import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import Band, DishMode


# pylint: disable=unused-argument,too-many-arguments
@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_track_and_track_stop_cmds(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
):
    """Test Track command"""

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

    dish_manager_proxy.ConfigureBand1(True)
    main_event_store.wait_for_value(DishMode.CONFIG)
    main_event_store.wait_for_value(DishMode.STANDBY_FP)
    band_event_store.wait_for_value(Band.B1, timeout=8)

    [[_], [unique_id]] = dish_manager_proxy.SetOperateMode()
    main_event_store.wait_for_command_id(unique_id, timeout=8)

    [[_], [unique_id]] = dish_manager_proxy.Track()

    main_event_store.wait_for_command_id(unique_id, timeout=8)

    expected_progress_updates = [
        "Track called on DS, ID",
        "Awaiting DS pointingstate change to [<PointingState.TRACK: 2>",
        "Track completed",
    ]

    # Wait for the track command to complete
    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    # Check that all the expected progress messages appeared
    # in the event store
    events_string = "".join([str(event) for event in events])

    for message in expected_progress_updates:
        assert message in events_string

    # Call TrackStop on DishManager
    [[_], [unique_id]] = dish_manager_proxy.TrackStop()

    main_event_store.wait_for_command_id(unique_id, timeout=8)

    expected_progress_updates = [
        "TrackStop called on DS, ID",
        "Awaiting DS pointingstate change to [<PointingState.READY",
        "TrackStop completed",
    ]

    # Wait for the track command to complete
    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=8
    )

    # Check that all the expected progress messages appeared
    # in the event store
    events_string = "".join([str(event) for event in events])

    for message in expected_progress_updates:
        assert message in events_string
