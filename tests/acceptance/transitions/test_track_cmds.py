"""Test that DS goes into Track and dishManager reports it."""

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
from tests.utils import remove_subscriptions, setup_subscriptions

TRACKING_POSITION_THRESHOLD_ERROR_DEG = 0.05
INIT_AZ = -250
INIT_EL = 70


@pytest.fixture
def slew_dish_to_init(event_store_class, dish_manager_proxy):
    """Fixture that slews the dish to a init position."""
    main_event_store = event_store_class()
    band_event_store = event_store_class()
    achieved_pointing_event_store = event_store_class()
    attr_cb_mapping = {
        "dishMode": main_event_store,
        "configuredBand": band_event_store,
        "achievedPointing": achieved_pointing_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    dish_manager_proxy.ConfigureBand1(True)
    main_event_store.wait_for_value(DishMode.CONFIG, timeout=10, proxy=dish_manager_proxy)
    band_event_store.wait_for_value(Band.B1, timeout=10)

    # Await auto transition to OPERATE following band config
    main_event_store.wait_for_value(DishMode.OPERATE, timeout=10, proxy=dish_manager_proxy)

    current_az, current_el = dish_manager_proxy.achievedPointing[1:]
    estimate_slew_duration = max(abs(INIT_EL - current_el), (abs(INIT_AZ - current_az) / 3))
    dish_manager_proxy.Slew([INIT_AZ, INIT_EL])

    # wait until no updates
    data_points = achieved_pointing_event_store.get_queue_values(
        timeout=estimate_slew_duration + 10
    )
    # timeout return empty list
    assert data_points
    # returned data is an array of tuple consisting of attribute name and value
    last_az_el = data_points[-1][1]
    # check last az and el received and compare with reference
    achieved_az, achieved_el = last_az_el[1], last_az_el[2]
    assert achieved_az == pytest.approx(INIT_AZ)
    assert achieved_el == pytest.approx(INIT_EL)
    remove_subscriptions(subscriptions)

    yield

    dish_manager_proxy.TrackStop()


@pytest.mark.xfail(
    reason="Transition to dish mode OPERATE only allowed through calling ConfigureBand_x."
)
@pytest.mark.acceptance
@pytest.mark.forked
def test_track_and_track_stop_cmds(
    slew_dish_to_init,
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
    ds_device_proxy,
):
    """Test call of Track command and stop."""
    pointing_state_event_store = event_store_class()
    result_event_store = event_store_class()
    progress_event_store = event_store_class()
    achieved_pointing_event_store = event_store_class()

    attr_cb_mapping = {
        "pointingState": pointing_state_event_store,
        "achievedPointing": achieved_pointing_event_store,
        "longRunningCommandProgress": progress_event_store,
        "longRunningCommandResult": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    assert dish_manager_proxy.dishMode == DishMode.OPERATE

    # Load a track table
    current_pointing = dish_manager_proxy.achievedPointing
    current_az = current_pointing[1]
    current_el = current_pointing[2]

    current_time_tai_s = ds_device_proxy.GetCurrentTAIOffset()

    # Directions to move values
    az_dir = 1 if current_az < 350 else -1
    el_dir = 1 if current_el < 80 else -1

    # create a long track table with last three reference positions the same
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
        current_time_tai_s + 20,
        current_az + 3 * az_dir,
        current_el + 3 * el_dir,
        current_time_tai_s + 30,
        current_az + 3 * az_dir,
        current_el + 3 * el_dir,
    ]
    final_position = track_table[-2:]

    dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.NEW
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
            abs(value[1] - final_position[0]) < TRACKING_POSITION_THRESHOLD_ERROR_DEG
            and abs(value[2] - final_position[1]) < TRACKING_POSITION_THRESHOLD_ERROR_DEG
        )

    achieved_pointing_event_store.clear_queue()
    achieved_pointing_event_store.wait_for_condition(check_final_points_reached, timeout=20)

    # Call TrackStop on DishManager
    [[_], [unique_id]] = dish_manager_proxy.TrackStop()
    result_event_store.wait_for_command_id(unique_id, timeout=60)
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

    remove_subscriptions(subscriptions)


@pytest.mark.xfail(
    reason="Transition to dish mode OPERATE only allowed through calling ConfigureBand_x. "
    "Modify fixture once the dish states and modes updates have been made on dish manager."
)
@pytest.mark.acceptance
@pytest.mark.forked
def test_append_dvs_case(
    slew_dish_to_init,
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
    ds_device_proxy,
):
    """Test Track with Append for DVS case."""
    pointing_state_event_store = event_store_class()
    result_event_store = event_store_class()
    achieved_pointing_event_store = event_store_class()
    attr_cb_mapping = {
        "pointingState": pointing_state_event_store,
        "achievedPointing": achieved_pointing_event_store,
        "longRunningCommandResult": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    assert dish_manager_proxy.dishMode == DishMode.OPERATE

    # Load a track table
    az_amplitude = 8
    az_sin_period = 100
    el_amplitude = 4
    el_sin_period = 100

    track_delay = 15
    samples_per_append = 5

    def generate_next_1_second_table(start_time, samples):
        sampling_time = 1 / samples
        track_table_temp = []
        for i in range(samples):
            timestamp = start_time + i * sampling_time
            azimuth = az_amplitude * sin(2 * pi * timestamp / az_sin_period) + INIT_AZ
            elevation = el_amplitude * sin(2 * pi * timestamp / el_sin_period) + INIT_EL
            track_table_temp.append(timestamp)
            track_table_temp.append(azimuth)
            track_table_temp.append(elevation)

        return track_table_temp

    start_tai = ds_device_proxy.GetCurrentTAIOffset() + track_delay
    track_table = generate_next_1_second_table(start_tai, samples_per_append)
    dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.NEW
    dish_manager_proxy.programTrackTable = track_table

    [[_], [unique_id]] = dish_manager_proxy.Track()
    result_event_store.wait_for_command_id(unique_id, timeout=8)
    pointing_state_event_store.wait_for_value(PointingState.SLEW, timeout=60)
    pointing_state_event_store.wait_for_value(PointingState.TRACK, timeout=60)

    number_of_1_second_appends = 20
    for _ in range(number_of_1_second_appends):
        # get last absolute time
        prev_start_tai = track_table[-3]
        start_tai = prev_start_tai + 1 / samples_per_append
        track_table = generate_next_1_second_table(start_tai, samples_per_append)
        dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.APPEND
        dish_manager_proxy.programTrackTable = track_table
        time.sleep(0.5)

    last_timestamp_in_table = track_table[-3]
    while ds_device_proxy.GetCurrentTAIOffset() < last_timestamp_in_table + 5:
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

    remove_subscriptions(subscriptions)


@pytest.mark.xfail(
    reason="Transition to dish mode OPERATE only allowed through calling ConfigureBand_x. "
    "Modify fixture once the dish states and modes updates have been made on dish manager."
)
@pytest.mark.acceptance
@pytest.mark.forked
def test_maximum_capacity(
    slew_dish_to_init,
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
    ds_device_proxy,
):
    """Test loading of track tables to maximum capacity."""
    pointing_state_event_store = event_store_class()
    result_event_store = event_store_class()
    achieved_pointing_event_store = event_store_class()
    current_index_event_store = event_store_class()
    end_index_event_store = event_store_class()
    attr_cb_mapping = {
        "pointingState": pointing_state_event_store,
        "achievedPointing": achieved_pointing_event_store,
        "trackTableCurrentIndex": current_index_event_store,
        "trackTableEndIndex": end_index_event_store,
        "longRunningCommandResult": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    assert dish_manager_proxy.dishMode == DishMode.OPERATE

    current_pointing = dish_manager_proxy.achievedPointing
    current_az = current_pointing[1]
    current_el = current_pointing[2]

    def generate_constant_table(
        start_time, dt_sample, samples, az_sample, el_sample
    ) -> list[float]:
        timestamp = start_time
        track_table = []
        for _ in range(samples):
            row = [timestamp, az_sample, el_sample]
            track_table.extend(row)
            timestamp += dt_sample

        return track_table

    track_delay = 50
    time_now = ds_device_proxy.GetCurrentTAIOffset()
    track_start_tai = time_now + track_delay
    duration_per_block_s = 5
    samples_per_block = 50
    sample_spacing = duration_per_block_s / samples_per_block
    # 50 samples covering 5 s is equivalent of a points spacing of
    # 5 / 50 = 0.1s
    # with a maximum table size of 10000
    # the total duration that can be capture in the track table is
    # 10000 * 0.1 = 1000s or ~ 17 minutes
    track_table = generate_constant_table(
        track_start_tai, sample_spacing, samples_per_block, current_az, current_el
    )
    # reset indexes with NEW load mode
    dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.NEW
    dish_manager_proxy.programTrackTable = track_table

    current_index_event_store.wait_for_value(1)
    expected_end_index = samples_per_block
    end_index_event_store.wait_for_value(expected_end_index)

    # append to fill up track table
    max_track_table_buffer_size = 10000
    max_track_table_load = int(max_track_table_buffer_size / samples_per_block)
    for _ in range(max_track_table_load - 1):
        # use last track table timestamp as a reference for start of new block
        start_tai = track_table[-3] + sample_spacing
        track_table = generate_constant_table(
            start_tai, sample_spacing, samples_per_block, current_az, current_el
        )
        dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.APPEND
        dish_manager_proxy.programTrackTable = track_table

        expected_end_index += samples_per_block
        end_index_event_store.wait_for_value(expected_end_index)

    # try to append to a full track table and expect failure
    start_tai = track_table[-3] + sample_spacing
    track_table = generate_constant_table(
        start_tai, sample_spacing, samples_per_block, current_az, current_el
    )
    dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.APPEND
    with pytest.raises(tango.DevFailed):
        dish_manager_proxy.programTrackTable = track_table

    # ensure load completed before track start time
    load_complete_time = ds_device_proxy.GetCurrentTAIOffset()
    assert track_start_tai > load_complete_time

    [[_], [unique_id]] = dish_manager_proxy.Track()
    result_event_store.wait_for_command_id(unique_id, timeout=8)
    pointing_state_event_store.wait_for_value(PointingState.SLEW, timeout=60)
    pointing_state_event_store.wait_for_value(PointingState.TRACK, timeout=60)

    # wait for tracking to start consuming table
    while ds_device_proxy.GetCurrentTAIOffset() < track_start_tai:
        time.sleep(5)
    # check that current index has moved from reset
    assert dish_manager_proxy.trackTableCurrentIndex > 0

    # wait for the first tracking block to be consumed so that space is available
    while ds_device_proxy.GetCurrentTAIOffset() < track_start_tai + duration_per_block_s:
        time.sleep(5)
    start_tai = track_table[-3] + sample_spacing
    track_table = generate_constant_table(
        start_tai, sample_spacing, samples_per_block, current_az, current_el
    )
    dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.APPEND
    dish_manager_proxy.programTrackTable = track_table
    # expect a roll over of the circular buffer
    expected_end_index = samples_per_block
    end_index_event_store.wait_for_value(expected_end_index)

    remove_subscriptions(subscriptions)


@pytest.mark.xfail(
    reason="Transition to dish mode OPERATE only allowed through calling ConfigureBand_x"
)
@pytest.mark.acceptance
@pytest.mark.forked
def test_track_fails_when_track_called_late(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
    ds_device_proxy,
):
    """Test Track command fails when the track table is no more valid."""
    main_event_store = event_store_class()
    band_event_store = event_store_class()
    pointing_state_event_store = event_store_class()
    attr_cb_mapping = {
        "dishMode": main_event_store,
        "configuredBand": band_event_store,
        "pointingState": pointing_state_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    dish_manager_proxy.ConfigureBand1(True)
    main_event_store.wait_for_value(DishMode.CONFIG, timeout=10, proxy=dish_manager_proxy)
    band_event_store.wait_for_value(Band.B1, timeout=10)

    # Await auto transition to OPERATE following band config
    main_event_store.wait_for_value(DishMode.OPERATE, timeout=10, proxy=dish_manager_proxy)

    assert dish_manager_proxy.dishMode == DishMode.OPERATE

    # Construct track table
    track_table_delay_s = 2
    start_time = ds_device_proxy.GetCurrentTAIOffset() + track_table_delay_s
    track_table_duration_s = 4
    track_table = []
    for i in range(track_table_duration_s):
        track_table.extend([start_time + i, INIT_AZ, INIT_EL])

    # Load the track table
    dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.NEW
    dish_manager_proxy.programTrackTable = track_table

    # wait until the table is not valid
    while ds_device_proxy.GetCurrentTAIOffset() <= track_table[-3] + 1:
        time.sleep(1)

    # we don't have any way yet to confirm that the track command failed
    dish_manager_proxy.Track()
    with pytest.raises(RuntimeError):
        pointing_state_event_store.wait_for_value(PointingState.TRACK, timeout=10)

    remove_subscriptions(subscriptions)
