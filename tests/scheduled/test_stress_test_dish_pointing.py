"""Test to stress test dish pointing by appending pointing coordinates at rate of 200ms"""

import logging
import time

import pytest
import tango
from pytest import approx

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
    PointingState,
    TrackTableLoadMode,
)
from ska_mid_dish_manager.utils.ska_epoch_to_tai import get_current_tai_timestamp

LOGGER = logging.getLogger(__name__)
NUMBER_OF_TABLE_SAMPLES = 300  # amounts to 6 calls to track table
TRACK_TABLE_LIMIT = 150

LEAD_TIME = 10
CADENCE_SEC = 0.2  # decided cadence is 1Hz but choosing quicker rate to stress test

TOLERANCE = 1e-2


@pytest.mark.stress
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
    band_event_store.wait_for_value(Band.B2)

    [[_], [unique_id]] = dish_manager_proxy.SetOperateMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    # start from a known arbitrary point
    pointing_state_event_store.clear_queue()
    dish_manager_proxy.Slew([0, 35])
    pointing_state_event_store.wait_for_value(PointingState.READY, timeout=300)

    # Dish goes to FP mode after moving. Request Operate again
    # TODO Remove this after bug is fixed
    [[_], [unique_id]] = dish_manager_proxy.SetOperateMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    # Generate NUMBER_OF_TABLE_SAMPLES sized list of pointing coords
    current_pointing = dish_manager_proxy.achievedPointing
    current_az = current_pointing[1]
    current_el = current_pointing[2]

    az_dir = 1 if current_az < 0 else -1
    el_dir = 1 if current_el < 45 else -1

    track_table = []
    loaded_sample_count = 0
    start_time_tai_s = get_current_tai_timestamp() + LEAD_TIME

    while loaded_sample_count < NUMBER_OF_TABLE_SAMPLES:
        track_table.extend(
            [
                start_time_tai_s + (loaded_sample_count * CADENCE_SEC),
                current_az + (0.025 * loaded_sample_count * az_dir),
                current_el + (0.025 * loaded_sample_count * el_dir),
            ]
        )
        loaded_sample_count += 1

    # Send first table in NEW mode
    dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.NEW
    dish_manager_proxy.programTrackTable = track_table[:TRACK_TABLE_LIMIT]
    dish_manager_proxy.Track()

    # Rapid fire the remaining entries in append mode
    dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.APPEND

    while True:
        try:
            track_table = track_table[TRACK_TABLE_LIMIT:]
        except IndexError:
            break
        if len(track_table) < TRACK_TABLE_LIMIT:
            break
        try:
            dish_manager_proxy.programTrackTable = track_table[:TRACK_TABLE_LIMIT]
        except tango.DevFailed:
            # log failed programTrackTable writes
            LOGGER.warning(
                "Writing track sample %s to programTrackTable failed",
                track_table[:TRACK_TABLE_LIMIT],
            )
        time.sleep(CADENCE_SEC)

    # Wait sufficient period of time for the track to complete
    pointing_state_values = pointing_state_event_store.get_queue_values(timeout=300)
    pointing_state_values = [event_value[1] for event_value in pointing_state_values]

    # Check that the dish transitioned through READY, SLEW and TRACK pointing states
    assert len(pointing_state_values) >= 2
    assert pointing_state_values.count(PointingState["TRACK"]) == 1
    assert pointing_state_values.count(PointingState["READY"]) >= 1
    # Dish may or may not SLEW depending on how close it is to the target
    assert pointing_state_values.count(PointingState["SLEW"]) >= 0

    destination_coord = dish_manager_proxy.programTrackTable
    last_requested_az = destination_coord[-2]
    last_requested_el = destination_coord[1]

    assert ds_device_proxy.achievedPointing[1] == approx(last_requested_az, rel=TOLERANCE)
    assert ds_device_proxy.achievedPointing[2] == approx(last_requested_el, rel=TOLERANCE)
