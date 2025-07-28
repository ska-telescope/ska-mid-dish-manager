"""Test to stress test dish pointing by appending pointing coordinates at rate of 200ms."""

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
from tests.utils import generate_track_table

LOGGER = logging.getLogger(__name__)
NUMBER_OF_TABLE_SAMPLES = 10  # amounts to 10 calls to track table
TRACK_TABLE_SIZE = 50  # maximum number of samples in track table

LEAD_TIME = 10
CADENCE_SEC = 0.2  # decided cadence is 1Hz but choosing quicker rate to stress test

TOLERANCE = 1e-2


@pytest.mark.xfail(
    reason="Transition to dish mode OPERATE only allowed through calling ConfigureBand_x"
)
@pytest.mark.stress
def test_stress_test_dish_pointing(dish_manager_proxy, ds_device_proxy, event_store_class):
    """Dish pointing stress test implementation."""
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
    pointing_state_event_store.clear_queue()

    # Send first table in NEW mode
    az, el = dish_manager_proxy.achievedPointing[1:]
    track_table = generate_track_table(
        num_samples=TRACK_TABLE_SIZE,
        current_az=az,
        current_el=el,
        time_offset_seconds=LEAD_TIME,
    )
    dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.NEW
    dish_manager_proxy.programTrackTable = track_table
    dish_manager_proxy.Track()

    # Rapid fire the remaining entries in append mode
    dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.APPEND
    for _ in range(NUMBER_OF_TABLE_SAMPLES - 1):
        tn, az, el = track_table[-3:]
        track_table = generate_track_table(
            num_samples=TRACK_TABLE_SIZE,
            current_az=az,
            current_el=el,
            time_offset_seconds=tn + LEAD_TIME,
        )
        try:
            dish_manager_proxy.programTrackTable = track_table
        except tango.DevFailed:
            # log failed programTrackTable writes
            LOGGER.warning(
                "Writing track sample %s to programTrackTable failed",
                track_table,
            )
        time.sleep(CADENCE_SEC)

    # Wait sufficient period of time for the track to complete
    pointing_state_values = pointing_state_event_store.get_queue_values(timeout=300)
    pointing_state_values = [event_value[1] for event_value in pointing_state_values]

    # Check that the dish transitioned through SLEW, TRACK and READY pointing states
    assert len(pointing_state_values) >= 3
    assert pointing_state_values.count(PointingState["SLEW"]) == 1, pointing_state_values
    assert pointing_state_values.count(PointingState["TRACK"]) == 1, pointing_state_values
    assert pointing_state_values.count(PointingState["READY"]) == 1, pointing_state_values

    destination_coord = dish_manager_proxy.programTrackTable
    last_requested_az = destination_coord[-2]
    last_requested_el = destination_coord[-1]

    assert ds_device_proxy.achievedPointing[1] == approx(last_requested_az, rel=TOLERANCE)
    assert ds_device_proxy.achievedPointing[2] == approx(last_requested_el, rel=TOLERANCE)
