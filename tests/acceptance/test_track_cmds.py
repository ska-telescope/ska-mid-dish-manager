"""Test that DS goes into Track and dishManager reports it"""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import Band, DishMode, PointingState
from ska_mid_dish_manager.utils import get_current_tai_timestamp


# pylint: disable=unused-argument,too-many-arguments,too-many-locals,too-many-statements
@pytest.mark.acceptance
@pytest.mark.forked
def test_track_and_track_stop_cmds(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
):
    """Test Track command"""
    band_event_store = event_store_class()
    dish_mode_event_store = event_store_class()
    pointing_state_event_store = event_store_class()
    result_event_store = event_store_class()
    progress_event_store = event_store_class()
    achieved_pointing_event_store = event_store_class()
    achieved_pointing_az_event_store = event_store_class()
    achieved_pointing_el_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        pointing_state_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "configuredBand",
        tango.EventType.CHANGE_EVENT,
        band_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "achievedPointing",
        tango.EventType.CHANGE_EVENT,
        achieved_pointing_event_store,
    )
    dish_manager_proxy.subscribe_event(
        "achievedPointingAz",
        tango.EventType.CHANGE_EVENT,
        achieved_pointing_az_event_store,
    )
    dish_manager_proxy.subscribe_event(
        "achievedPointingEl",
        tango.EventType.CHANGE_EVENT,
        achieved_pointing_el_event_store,
    )

    [[_], [unique_id]] = dish_manager_proxy.SetStandbyFPMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    dish_manager_proxy.ConfigureBand1(True)
    dish_mode_event_store.wait_for_value(DishMode.CONFIG)
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP)
    band_event_store.wait_for_value(Band.B1, timeout=8)

    [[_], [unique_id]] = dish_manager_proxy.SetOperateMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    # Load a track table
    current_pointing = dish_manager_proxy.achievedPointing
    current_az = current_pointing[1]
    current_el = current_pointing[2]

    current_time_tai_s = get_current_tai_timestamp()

    # Directions to move values
    az_dir = 1 if current_az < 350 else -1
    el_dir = 1 if current_el < 80 else -1

    track_table = [
        current_time_tai_s + 3,
        current_az + 1 * az_dir,
        current_el + 1 * el_dir,
        current_time_tai_s + 5,
        current_az + 2 * az_dir,
        current_el + 2 * el_dir,
        current_time_tai_s + 7,
        current_az + 3 * az_dir,
        current_el + 3 * el_dir,
        current_time_tai_s + 9,
        current_az + 4 * az_dir,
        current_el + 4 * el_dir,
        current_time_tai_s + 11,
        current_az + 5 * az_dir,
        current_el + 5 * el_dir,
    ]
    first_table_entry = [track_table[0], track_table[1], track_table[2]]
    second_table_entry = [track_table[3], track_table[4], track_table[5]]
    third_table_entry = [track_table[6], track_table[7], track_table[8]]

    dish_manager_proxy.programTrackTable = track_table

    [[_], [unique_id]] = dish_manager_proxy.Track()
    result_event_store.wait_for_command_id(unique_id, timeout=8)
    pointing_state_event_store.wait_for_value(PointingState.SLEW, timeout=6)
    pointing_state_event_store.wait_for_value(PointingState.TRACK, timeout=6)

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

    # Ensure that we pass through the first three points
    for table_entry in [first_table_entry, second_table_entry, third_table_entry]:
        # Check achievedPointing
        achieved_pointing_event_store.wait_for_value(table_entry, timeout=4)

        # Check achievedPointingAz and achievedPointingEl
        entry_az = [table_entry[0], table_entry[1]]
        entry_el = [table_entry[0], table_entry[2]]

        achieved_pointing_az_event_store.wait_for_value(entry_az, timeout=4)
        achieved_pointing_el_event_store.wait_for_value(entry_el, timeout=4)

    # Call TrackStop on DishManager
    [[_], [unique_id]] = dish_manager_proxy.TrackStop()
    result_event_store.wait_for_command_id(unique_id, timeout=8)
    pointing_state_event_store.wait_for_value(PointingState.READY, timeout=4)

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
