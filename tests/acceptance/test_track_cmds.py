"""Test that DS goes into Track and dishManager reports it"""

import time
from math import pi, sin

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
    PointingState,
    TrackTableLoadMode,
)
from ska_mid_dish_manager.utils.ska_epoch_to_tai import get_current_tai_timestamp

TRACKING_POSITION_THRESHOLD_ERROR_DEG = 0.05


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
    final_table_entry = [track_table[6], track_table[7], track_table[8]]

    dish_manager_proxy.programTrackTable = track_table

    [[_], [unique_id]] = dish_manager_proxy.Track()
    result_event_store.wait_for_command_id(unique_id, timeout=8)
    pointing_state_event_store.wait_for_value(PointingState.SLEW, timeout=6)
    pointing_state_event_store.wait_for_value(PointingState.TRACK, timeout=6)

    expected_progress_updates = [
        "Track called on DS, ID",
        (
            "Track command has been executed on DS. "
            "Monitor the achievedTargetLock attribute to determine when the dish is on source."
        ),
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

    # Check that we get to last entry
    def check_final_points_reached(value: any) -> bool:
        return (
            abs(value[1] - final_table_entry[1]) < TRACKING_POSITION_THRESHOLD_ERROR_DEG
            and abs(value[2] - final_table_entry[2]) < TRACKING_POSITION_THRESHOLD_ERROR_DEG
        )

    achieved_pointing_event_store.clear_queue()
    achieved_pointing_event_store.wait_for_condition(check_final_points_reached, timeout=10)

    # Call TrackStop on DishManager
    [[_], [unique_id]] = dish_manager_proxy.TrackStop()
    result_event_store.wait_for_command_id(unique_id, timeout=8)
    pointing_state_event_store.wait_for_value(PointingState.READY, timeout=4)

    expected_progress_updates = [
        "TrackStop called on DS, ID",
        "Awaiting DS pointingstate change to READY",
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


@pytest.mark.acceptance
@pytest.mark.forked
def test_append(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
):
    """Test Track with Append"""
    band_event_store = event_store_class()
    dish_mode_event_store = event_store_class()
    pointing_state_event_store = event_store_class()
    result_event_store = event_store_class()
    progress_event_store = event_store_class()
    achieved_pointing_event_store = event_store_class()

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

    [[_], [unique_id]] = dish_manager_proxy.SetStandbyFPMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    dish_manager_proxy.ConfigureBand1(True)
    dish_mode_event_store.wait_for_value(DishMode.CONFIG)
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP)
    band_event_store.wait_for_value(Band.B1, timeout=8)

    [[_], [unique_id]] = dish_manager_proxy.SetOperateMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    # Slew to valid tracking region
    init_az = -250
    init_el = 70
    dish_manager_proxy.Slew([init_az, init_el])
    pointing_state_event_store.wait_for_value(PointingState.SLEW, timeout=6)
    pointing_state_event_store.wait_for_value(PointingState.READY, timeout=60)

    # Load a track table
    az_amplitude = 8
    az_sin_period = 100
    el_amplitude = 4
    el_sin_period = 100

    track_delay = 10
    samples_per_append = 5

    def generate_next_1_second_table(start_time, samples):
        sampling_time = 1 / samples
        track_table_temp = []
        for i in range(samples):
            timestamp = start_time + i * sampling_time
            azimuth = az_amplitude * sin(2 * pi * timestamp / az_sin_period) + init_az
            elevation = el_amplitude * sin(2 * pi * timestamp / el_sin_period) + init_el
            track_table_temp.append(timestamp)
            track_table_temp.append(azimuth)
            track_table_temp.append(elevation)

        return track_table_temp

    start_tai = get_current_tai_timestamp() + track_delay
    track_table = generate_next_1_second_table(start_tai, samples_per_append)
    dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.NEW
    dish_manager_proxy.programTrackTable = track_table

    [[_], [unique_id]] = dish_manager_proxy.Track()
    result_event_store.wait_for_command_id(unique_id, timeout=8)
    pointing_state_event_store.wait_for_value(PointingState.SLEW, timeout=10)
    pointing_state_event_store.wait_for_value(PointingState.TRACK, timeout=60)

    number_of_1_second_appends = 20
    for _ in range(number_of_1_second_appends):
        # get last absolute time
        prev_start_tai = track_table[-3]
        start_tai = prev_start_tai + 1 / samples_per_append
        track_table = generate_next_1_second_table(start_tai, samples_per_append)
        dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.APPEND
        dish_manager_proxy.programTrackTable = track_table
        time.sleep(1)

    # Check that we get to last entry
    def check_final_points_reached(value: any) -> bool:
        final_az = track_table[-2]
        final_el = track_table[-1]

        return (
            abs(value[1] - final_az) < TRACKING_POSITION_THRESHOLD_ERROR_DEG
            and abs(value[2] - final_el) < TRACKING_POSITION_THRESHOLD_ERROR_DEG
        )

    achieved_pointing_event_store.clear_queue()
    achieved_pointing_event_store.wait_for_condition(check_final_points_reached, timeout=10)

    # Call TrackStop on DishManager
    [[_], [unique_id]] = dish_manager_proxy.TrackStop()
    result_event_store.wait_for_command_id(unique_id, timeout=8)
    pointing_state_event_store.wait_for_value(PointingState.READY, timeout=4)

    expected_progress_updates = [
        "TrackStop called on DS, ID",
        "Awaiting DS pointingstate change to READY",
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
