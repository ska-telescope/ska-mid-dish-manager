"""Test tracking with data from a csv file."""

import csv
import time
from collections.abc import Generator
from typing import Any

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
    PointingState,
    TrackTableLoadMode,
)
from tests.data import RADIAL_CSV_PATH, SPIRAL_CSV_PATH

TRACKING_TABLE_CHUNK_SIZE = 50
TRACKING_TABLE_LOAD_LEAD_TIME_S = 5

TRACKING_TIME_THRESHOLD_ERROR_MS = 0.05  # 50ms cadence / tolerance
TRACKING_POSITION_THRESHOLD_ERROR_DEG = 1e6


def load_csv_data(file_path: str) -> list[tuple[float, float, float]]:
    """Loads the entire CSV file into memory."""
    data = []
    with open(file_path, newline="") as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)  # Skip header if present
        data = [(float(row[0]), float(row[1]), float(row[2])) for row in reader]
    return data


@pytest.mark.forked
@pytest.mark.track_patterns
@pytest.mark.parametrize(
    "track_csv_file",
    [
        (RADIAL_CSV_PATH),
        (SPIRAL_CSV_PATH),
    ],
)
def test_track_pattern(
    track_csv_file: Any,
    event_store_class: Any,
    dish_manager_proxy: tango.DeviceProxy,
    ds_device_proxy: tango.DeviceProxy,
    plot_dish_manager_pointing: Generator,
) -> None:
    """Test tracking the points from the given csv file."""
    main_event_store = event_store_class()
    pointing_event_store = event_store_class()
    end_index_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "dishmode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )
    dish_manager_proxy.subscribe_event(
        "pointingstate",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )
    dish_manager_proxy.subscribe_event(
        "configuredband",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )
    dish_manager_proxy.subscribe_event(
        "achievedPointing",
        tango.EventType.CHANGE_EVENT,
        pointing_event_store,
    )
    dish_manager_proxy.subscribe_event(
        "trackTableEndIndex",
        tango.EventType.CHANGE_EVENT,
        end_index_event_store,
    )

    # Get the dish ready for tracking
    dish_manager_proxy.SetStandbyFPMode()
    main_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=5)
    if dish_manager_proxy.configuredBand != Band.B1:
        dish_manager_proxy.ConfigureBand1(True)
        main_event_store.wait_for_value(Band.B1, timeout=60)
    dish_manager_proxy.SetOperateMode()
    main_event_store.wait_for_value(DishMode.OPERATE, timeout=5)

    data = load_csv_data(track_csv_file)
    total_points = len(data)

    # Slew to the start point
    _, start_point_az, start_point_el = data[0]
    dish_manager_proxy.Slew([start_point_az, start_point_el])

    # wait until no updates
    pointing_event_store.get_queue_values(timeout=5)

    start_time_tai = ds_device_proxy.GetCurrentTAIOffset() + 10

    # Get some checkpoints to ensure the dish passes through them
    checkpoints = [
        data[int(total_points * (1 / 4)) - 1],
        data[int(total_points * (1 / 2)) - 1],
        data[int(total_points * (3 / 4)) - 1],
        data[int(total_points * (1)) - 1],
    ]
    # Add the start time to the offsets in the checkpoints
    for i, checkpoint in enumerate(checkpoints):
        checkpoints[i] = (
            checkpoint[0] + float(start_time_tai),
            checkpoint[1],
            checkpoint[2],
        )

    # Ensure the first table load is done with TrackTableLoadMode.NEW
    dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.NEW

    # Loop to load points from the csv file
    first_load = True
    chunk_index = 0
    time_of_last_point_in_chunk = 0

    try:
        while True:
            if not first_load:
                time.sleep(0.5)

                if dish_manager_proxy.pointingState not in [
                    PointingState.TRACK,
                    PointingState.SLEW,
                ]:
                    assert 0, (
                        "Something went wrong, PointingState should be TRACK or SLEW but got"
                        f" {dish_manager_proxy.pointingState.name}."
                        f" AchievedPointing = {dish_manager_proxy.achievedpointing}."
                        f" trackTableCurrentIndex = {dish_manager_proxy.trackTableCurrentIndex}"
                    )
                # Ensure points are loaded with TRACKING_TABLE_LOAD_LEAD_TIME_S lead time
                elif (
                    time_of_last_point_in_chunk - ds_device_proxy.GetCurrentTAIOffset()
                    > TRACKING_TABLE_LOAD_LEAD_TIME_S
                ):
                    continue

            # Get the next chunk
            chunk = data[chunk_index : chunk_index + TRACKING_TABLE_CHUNK_SIZE]
            if not chunk:
                # No more data to load, break and wait for the track to complete
                break
            chunk_index += TRACKING_TABLE_CHUNK_SIZE

            # Generate the track table (adding the start time to each of the offsets)
            track_table: list[Any] = []
            for offset_tai, az, el in chunk:
                track_table += [start_time_tai + offset_tai, az, el]
            time_of_last_point_in_chunk = track_table[-3]

            # Load the track table chunk
            end_index_event_store.clear_queue()
            dish_manager_proxy.programTrackTable = track_table

            # Start tracking after loading first part of the table and then set
            # the track table load mode to APPEND
            if first_load:
                dish_manager_proxy.Track()
                main_event_store.wait_for_value(PointingState.TRACK, timeout=100)
                dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.APPEND
                first_load = False
            else:
                # TODO: PLC end index updates unexpectedly (1000 -> 1952, where 2000 was expected)
                # expected_next_end_index = ((end_index + len(chunk) - 1) % 10000) + 1
                # end_index_event_store.wait_for_value(expected_next_end_index, timeout=5)

                # Solution until above comment is resolved
                end_index_event_store.wait_for_n_events(1, timeout=5)

        # Wait for the track to finish
        final_tai_value = start_time_tai + data[-1][0]
        wait_duration = final_tai_value - ds_device_proxy.GetCurrentTAIOffset()
        wait_duration *= 1.10  # 10% leeway

        main_event_store.wait_for_value(PointingState.READY, timeout=wait_duration)
    finally:
        dish_manager_proxy.TrackStop()

    # Go through the pointing events received to make sure all the defined checkpoints were hit
    pointing_events = pointing_event_store.get_queue_values()

    search_index = 0
    checkpoints_found = [False] * len(checkpoints)
    for checkpoint_index, (cp_tai, cp_az, cp_el) in enumerate(checkpoints):
        # If the checkpoint is the same as the start point then no change events would be received.
        # So, mark it as found and move on
        if cp_az == start_point_az and cp_el == start_point_el:
            checkpoints_found[checkpoint_index] = True

        position_at_checkpoint_time = (0, 0)

        while search_index < len(pointing_events):
            _, (pointing_tai, pointing_az, pointing_el) = pointing_events[search_index]
            search_index += 1

            if abs(pointing_tai - cp_tai) < TRACKING_TIME_THRESHOLD_ERROR_MS:
                position_at_checkpoint_time = (pointing_az, pointing_el)
                checkpoints_found[checkpoint_index] = (
                    abs(pointing_az - cp_az) < TRACKING_POSITION_THRESHOLD_ERROR_DEG
                    and abs(pointing_el - cp_el) < TRACKING_POSITION_THRESHOLD_ERROR_DEG
                )
            if checkpoints_found[checkpoint_index]:
                break
        if not checkpoints_found[checkpoint_index]:
            print(
                f"Missed checkpoint ({cp_tai}, {cp_az}, {cp_el}). Point at the given time: "
                f"({position_at_checkpoint_time[0]}, {position_at_checkpoint_time[1]})"
            )

    assert all(checkpoints_found)
