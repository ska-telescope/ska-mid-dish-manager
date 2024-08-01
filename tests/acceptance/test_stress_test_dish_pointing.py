"""Test to stress test dish pointing by appending pointing coordinates at rate of 200ms"""
import time

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
    PointingState,
    TrackTableLoadMode,
)
from ska_mid_dish_manager.utils.ska_epoch_to_tai import get_current_tai_timestamp

NUMBER_OF_TABLE_SAMPLES = 1500
INIT_TABLE_SIZE = 5

TRACK_START_DELAY = 8
TRACK_APPEND_DELAY = 10

CADENCE_SEC = 0.2


# pylint:disable=too-many-locals
@pytest.mark.scheduled
def test_stress_test_dish_pointing(dish_manager_proxy, ds_device_proxy, event_store_class):
    """Dish pointing stress test implementation"""
    result_event_store = event_store_class()
    dish_mode_event_store = event_store_class()
    band_event_store = event_store_class()
    pointing_state_event_store = event_store_class()

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
        "configuredBand",
        tango.EventType.CHANGE_EVENT,
        band_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        pointing_state_event_store,
    )

    # Mode and configuration setup
    [[_], [unique_id]] = dish_manager_proxy.SetStandbyFPMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    dish_manager_proxy.ConfigureBand2(True)
    dish_mode_event_store.wait_for_value(DishMode.CONFIG)
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP)
    band_event_store.wait_for_value(Band.B2, timeout=8)

    [[_], [unique_id]] = dish_manager_proxy.SetOperateMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    # Generate NUMBER_OF_TABLE_SAMPLES sized list of pointing coords
    current_pointing = dish_manager_proxy.achievedPointing
    current_az = current_pointing[1]
    current_el = current_pointing[2]

    az_dir = 1 if current_az < 350 else -1
    el_dir = 1 if current_el < 80 else -1

    pointing_coord_list = []
    loaded_sample_count = 0

    while loaded_sample_count < NUMBER_OF_TABLE_SAMPLES:
        pointing_coord_list.extend(
            [
                current_az + (0.025 * loaded_sample_count * az_dir),
                current_el + (0.025 * loaded_sample_count * el_dir),
            ]
        )
        loaded_sample_count += 1

    # Generate 5 entry track table to start the track using first 5 coords
    start_time_tai_s = get_current_tai_timestamp() + TRACK_START_DELAY
    initial_table_timestamps = []
    for count in range(5):
        initial_table_timestamps.append((start_time_tai_s + (count * CADENCE_SEC)))

    initial_track_table = []
    for i in range(INIT_TABLE_SIZE):
        initial_track_table.extend(
            [
                initial_table_timestamps[i],
                pointing_coord_list[(i * 2)],
                pointing_coord_list[(i * 2) + 1],
            ]
        )

    dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.NEW
    dish_manager_proxy.programTrackTable = initial_track_table

    dish_manager_proxy.Track()
    pointing_state_event_store.wait_for_value(PointingState.SLEW, timeout=6)

    # Slice the first 5 coords out and rapid fire the remaining entries in append mode
    pointing_coord_list = pointing_coord_list[10:]
    dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.APPEND

    count = 0
    while count < len(pointing_coord_list):
        point_timestamp = get_current_tai_timestamp() + TRACK_APPEND_DELAY
        point_az = pointing_coord_list[count]
        point_el = pointing_coord_list[count + 1]
        time.sleep(CADENCE_SEC)
        dish_manager_proxy.programTrackTable = [point_timestamp, point_az, point_el]
        count += 2

    # Ensure achievedPointing reaches the final coordinate provided following coord streaming
    destination_coord = dish_manager_proxy.programTrackTable
    achieved_pointing_store = event_store_class()
    ds_device_proxy.subscribe_event(
        "achievedPointing",
        tango.EventType.CHANGE_EVENT,
        achieved_pointing_store,
    )
    assert achieved_pointing_store.wait_for_value(destination_coord, timeout=60)
