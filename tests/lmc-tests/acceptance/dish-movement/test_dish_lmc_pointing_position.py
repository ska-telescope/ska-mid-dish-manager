"""
Verify that dish lmc receives timestamped Az/El control commands

(R.LMC.CC.13, R.LMC.CC.14, R.LMC.FMD.2, R.LMC.SM.3)
"""

import logging
import time

import pytest
import tango
from pytest import approx
from pytest_bdd import given, scenario, then, when
from pytest_bdd.parsers import parse
from utils import EventStore, retrieve_attr_value

from ska_mid_dish_manager.models.dish_enums import PointingState

# pylint: disable=too-many-locals

LOGGER = logging.getLogger(__name__)

# constants are from the dish simulator behaviour
# Use elevation to estimate time expected to arrive on target since
# it moves slower
MAX_DESIRED_AZIM = 270.0
MAX_DESIRED_ELEV = 90.0
ELEV_DRIVE_MAX_RATE = 1.0
TOLERANCE = 1e-2  # MeerKAT lock threshold


@pytest.fixture(scope="module")
def pointing_state_event_store():
    """Fixture for storing events"""
    return EventStore()


@pytest.mark.acceptance
@scenario("XTP-5414.feature", "Test dish pointing request")
def test_dish_pointing(monitor_tango_servers):
    # pylint: disable=missing-function-docstring
    pass


@given(parse("dish_manager dishMode reports {dish_mode}"))
def check_dish_manager_dish_mode(dish_mode, dish_manager, modes_helper):
    # pylint: disable=missing-function-docstring
    modes_helper.ensure_dish_manager_mode(dish_mode)
    current_dish_mode = retrieve_attr_value(dish_manager, "dishMode")
    LOGGER.info(f"{dish_manager} dishMode: {current_dish_mode}")


@given(parse("dish_manager pointingState reports {pointing_state}"))
def dish_reports_allowed_pointing_state(pointing_state, dish_manager, pointing_state_event_store):
    # pylint: disable=missing-function-docstring
    dish_manager.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        pointing_state_event_store,
    )
    pointing_state_event_store.wait_for_value(PointingState[pointing_state], timeout=60)
    current_pointing_state = retrieve_attr_value(dish_manager, "pointingState")
    assert current_pointing_state == pointing_state
    LOGGER.info(f"{dish_manager} pointingState: {current_pointing_state}")


@when(
    parse(
        "I issue Track on dish_manager to move azimuth " "and elevation by {delta:g} degrees each"
    )
)
def request_pointing_position(delta, dish_manager):
    # pylint: disable=missing-function-docstring
    # determine the az, el coordinates
    az, el = dish_manager.achievedPointing[1:]
    # Startup values for az, el are [0, 0]. If the requested
    # delta is less than 15 deg the elevation will not be within
    # the mechanical limit. Adjust elevation before adding delta
    el = el + 10 if el < 5 else el

    # azimuth
    if az + delta >= MAX_DESIRED_AZIM:
        az -= delta
    else:
        az += delta
    # elevation
    if el + delta >= MAX_DESIRED_ELEV:
        el -= delta
    else:
        el += delta

    # the az,el coordinates sent to dish master must have a
    # future timestamp in order for them to be considered
    cmd_time_offset = 5000  # milliseconds
    dish_manager.desiredPointing = [
        time.time() * 1000.0 + cmd_time_offset,
        az,
        el,
    ]
    # transitions to SLEW pointingState
    dish_manager.Track()

    el_delta = abs(el - dish_manager.desiredPointing[2])
    expected_time_to_move = el_delta / ELEV_DRIVE_MAX_RATE
    # add an arbitrary 60s el time tolerance
    future_time = time.time() + expected_time_to_move + 60
    dish_far_from_requested_position = True
    extra_coordinates_sent = False

    while dish_far_from_requested_position:
        # keep sending the coordinates every 200ms spaced at the offset
        dish_manager.desiredPointing = [
            time.time() * 1000.0 + cmd_time_offset,
            az,
            el,
        ]
        time.sleep(0.2)
        desired_az, desired_el = dish_manager.desiredPointing[1:3]
        achieved_az, achieved_el = dish_manager.achievedPointing[1:]
        az_close_enough = desired_az == approx(achieved_az, rel=TOLERANCE)
        el_close_enough = desired_el == approx(achieved_el, rel=TOLERANCE)
        dish_close_to_configured_threshold = az_close_enough and el_close_enough

        # Dish will report SLEW when it's moving to the requested position
        if dish_manager.pointingState.name == "SLEW":
            LOGGER.info("Slewing to target")

        # when the dish arrives on target the pointingState will
        # transition to TRACK if you keep sending in coordinates
        if dish_manager.pointingState.name == "TRACK":
            LOGGER.info("Tracking target")
            # pointingState will go back to READY
            # when no more new coordinates arrive
            if not extra_coordinates_sent:
                extra_coordinates_sent = True
            if dish_close_to_configured_threshold:
                dish_far_from_requested_position = False

        if future_time < time.time():
            break


@then(
    "the difference between actual and desired azimuth "
    "should be less than or equal to the configured threshold"
)
def check_azimuth_position(
    dish_manager,
    dish_structure,
):
    # pylint: disable=missing-function-docstring
    # checking DISHMASTER az values
    desired_az, achieved_az = (
        dish_manager.desiredPointing[1],
        dish_manager.achievedPointing[1],
    )
    assert desired_az == approx(achieved_az, rel=TOLERANCE)

    # checking DISHSTRUCTURE az values
    desired_az, achieved_az = (
        dish_structure.desiredPointing[1],
        dish_structure.achievedPointing[1],
    )
    assert desired_az == approx(achieved_az, rel=TOLERANCE)

    LOGGER.info(
        f"{dish_manager} and {dish_structure} devices arrived at the requested azimuth position"
    )


@then(
    "the difference between actual and desired elevation "
    "should be less than or equal to the configured threshold"
)
def check_elevation_position(
    dish_manager,
    dish_structure,
):
    # pylint: disable=missing-function-docstring
    # checking DISHMASTER el values
    desired_el, achieved_el = (
        dish_manager.desiredPointing[2],
        dish_manager.achievedPointing[2],
    )
    assert desired_el == approx(achieved_el, rel=TOLERANCE)

    # checking DISHSTRUCTURE el values
    desired_el, achieved_el = (
        dish_structure.desiredPointing[2],
        dish_structure.achievedPointing[2],
    )
    assert desired_el == approx(achieved_el, rel=TOLERANCE)

    LOGGER.info(
        f"{dish_manager} and {dish_structure} devices arrived at the requested elevation position"
    )


@then(parse("dish_manager pointingState should transition to {track} on target"))
def check_pointing_state_on_target(track, dish_manager, pointing_state_event_store):
    # pylint: disable=missing-function-docstring
    pointing_state_event_store.wait_for_value(PointingState[track], timeout=60)

    pointing_state = dish_manager.PointingState
    LOGGER.info(f"{dish_manager} pointingState: {pointing_state}")


@then("dish_manager and dish_structure should report" " the same achieved pointing position")
def check_dish_manager_dish_structure_position(
    dish_manager,
    dish_structure,
):
    # pylint: disable=missing-function-docstring
    dish_manager_achieved_az_el = dish_manager.achievedPointing[1:3]
    dish_structure_achieved_az_el = dish_structure.achievedPointing[1:3]

    assert list(dish_manager_achieved_az_el) == list(dish_structure_achieved_az_el)

    LOGGER.info(f"{dish_manager} and {dish_structure} devices report the same achieved position")
