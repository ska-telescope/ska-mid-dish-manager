import logging

import pytest
import tango
import time
from dish_enums import PointingState
from pytest_bdd import given, scenario, then, when
from pytest_bdd.parsers import parse
from utils import retrieve_attr_value

LOGGER = logging.getLogger(__name__)


@pytest.mark.acceptance
@scenario("XTP-22210.feature", "Test Dish TrackStop command")
def test_dish_track_stop_command(monitor_tango_servers):
    # pylint: disable=missing-function-docstring
    pass


@given(parse("dish_manager dishMode reports {dish_mode}"))
def check_dish_manager_dish_mode(dish_mode, dish_manager, modes_helper):
    # pylint: disable=missing-function-docstring
    modes_helper.ensure_dish_manager_mode(dish_mode)
    current_dish_mode = retrieve_attr_value(dish_manager, "dishMode")
    LOGGER.info(f"{dish_manager} dishMode: {current_dish_mode}")


@given("dish_manager pointingState reports TRACK or SLEW")
def dish_reports_required_pointing_state(
    dish_manager, dish_manager_event_store
):
    dish_manager.subscribe_event(
        f"pointingState",
        tango.EventType.CHANGE_EVENT,
        dish_manager_event_store,
    )

    cmd_time_offset = 500 # ms offset

    # desired pointing takes a timestamp, azimuthm, and elevation
    dish_manager.desiredPointing = [
        time.time() * 1000.0 + cmd_time_offset,
        50,
        45
    ]

    dish_manager.Track()

    dish_manager_event_store.wait_for_value(PointingState.SLEW)

    current_pointing_state = retrieve_attr_value(dish_manager, "pointingState")
    assert current_pointing_state in [PointingState.TRACK.name, PointingState.SLEW.name]
    LOGGER.info(f"{dish_manager} pointingState: {current_pointing_state}")

@given("dish_structure pointingState reports TRACK or SLEW")
def dish_structure_reports_required_pointing_state(
    dish_structure
):
    current_pointing_state = retrieve_attr_value(dish_structure, "pointingState")
    assert current_pointing_state in [PointingState.TRACK.name, PointingState.SLEW.name]
    LOGGER.info(f"{dish_structure} pointingState: {current_pointing_state}")


@when("I issue TrackStop on dish_manager")
def issue_track_stop_on_dish(dish_manager):
    dish_manager.TrackStop()

@then(
    parse(
        "dish_manager pointingState should transition to {pointing_state}"
    )
)
def dish_manager_transitions_to_expected_pointing_state(
    pointing_state, dish_manager, dish_manager_event_store
):
    # pylint: disable=missing-function-docstring
    dish_manager_event_store.wait_for_value(
        PointingState[pointing_state], timeout=60
    )
    current_pointing_state = retrieve_attr_value(dish_manager, "pointingState")
    LOGGER.info(f"{dish_manager} pointingState: {current_pointing_state}")

@then(
    parse(
        "dish_structure pointingState should transition to {pointing_state}"
    )
)
def dish_structure_transitions_to_expected_pointing_state(
    pointing_state,
    dish_structure
):
    # pylint: disable=missing-function-docstring
    current_pointing_state = retrieve_attr_value(dish_structure, "pointingState")
    assert current_pointing_state == pointing_state
    LOGGER.info(f"{dish_structure} pointingState: {current_pointing_state}")
