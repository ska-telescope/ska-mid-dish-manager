"""Verify that dish transitions to STOW from allowed modes

(R.LMC.SM.12, R.LMC.SM.1, R.LMC.SM.2, R.LMC.SM.6,
R.LMC.SM.22 except MAINTENANCE)
"""

import logging
import time

import pytest
import tango
from pytest import approx
from pytest_bdd import given, scenario, then, when
from pytest_bdd.parsers import parse
from utils import retrieve_attr_value, EventStore

from ska_mid_dish_manager.models.dish_enums import PointingState

LOGGER = logging.getLogger(__name__)

# elevation drive rate is from the simulator behaviour
ELEV_DRIVE_MAX_RATE = 1.0
TOLERANCE = 1e-2


@pytest.fixture(scope="module")
def pointing_state_event_store():
    """Fixture for storing events"""
    return EventStore()


@pytest.fixture(scope="module", name="initial_az")
def fixture_initial_az():
    # pylint: disable=missing-function-docstring
    return {"az": 0}


@pytest.mark.acceptance
@scenario("XTP-3090.feature", "Test dish stow request")
def test_stow_command(monitor_tango_servers):
    # pylint: disable=missing-function-docstring
    pass


@given(
    "dish_manager dishMode reports any allowed dishMode for SetStowMode command"
)
def dish_reports_allowed_dish_mode(dish_manager):
    # pylint: disable=missing-function-docstring
    allowed_dish_modes = [
        "OFF",
        "STARTUP",
        "SHUTDOWN",
        "STANDBY_LP",
        "STANDBY_FP",
        "MAINTENANCE",
        "CONFIG",
        "OPERATE",
        "STOW",
    ]
    current_dish_mode = retrieve_attr_value(dish_manager, "dishMode")
    assert current_dish_mode in allowed_dish_modes
    LOGGER.info(f"{dish_manager} dishMode: {current_dish_mode}")


@when("I issue SetStowMode on dish_manager")
def set_stow_mode(
    dish_manager, pointing_state_event_store, initial_az, modes_helper
):
    # pylint: disable=missing-function-docstring
    dish_manager.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        pointing_state_event_store,
    )

    initial_az["az"] = dish_manager.achievedPointing[1]
    initial_el = dish_manager.achievedPointing[2]
    LOGGER.info(f"{dish_manager} initial azimuth: {initial_az['az']}")
    LOGGER.info(f"{dish_manager} initial elevation: {initial_el}")

    modes_helper.dish_manager_go_to_mode("STOW")
    LOGGER.info(f"{dish_manager} requested dishMode: STOW")


@then("dish_manager dishMode should report STOW")
def check_dish_mode(
    dish_manager,
):
    # pylint: disable=missing-function-docstring
    current_dish_mode = retrieve_attr_value(dish_manager, "dishMode")
    assert current_dish_mode == "STOW"
    LOGGER.info(f"{dish_manager} dishMode: {current_dish_mode}")


@then("dish_structure operatingMode should report STOW")
def check_ds_operating_mode(
    dish_structure,
):
    # pylint: disable=missing-function-docstring
    current_operating_mode = retrieve_attr_value(
        dish_structure, "operatingMode"
    )
    assert current_operating_mode == "STOW"
    LOGGER.info(f"{dish_structure} operatingMode: {current_operating_mode}")


@then(
    parse(
        "dish_manager and dish_structure elevation should be greater than or equal to {stow_position:g}"
    )
)
def check_dish_manager_dish_structure_el_position(
    stow_position,
    dish_manager,
    dish_structure,
):
    # pylint: disable=missing-function-docstring
    el_delta = abs(stow_position - dish_manager.desiredPointing[2])
    expected_time_to_move = el_delta / ELEV_DRIVE_MAX_RATE
    # add an arbitrary 10s el time tolerance
    future = time.time() + expected_time_to_move + 10
    dish_far_from_stow_position = True

    while dish_far_from_stow_position:
        now = time.time()
        current_el = dish_manager.desiredPointing[2]
        dish_far_from_stow_position = not (
            stow_position == approx(current_el, rel=TOLERANCE)
        )
        # sleep to avoid using full CPU resources
        # while waiting to arrive on target
        time.sleep(1)
        if future < now:
            break

    # checking DISHMASTER el values
    current_el = dish_manager.achievedPointing[2]
    assert current_el == approx(stow_position, rel=TOLERANCE)

    # checking DISHSTRUCTURE el values
    current_el = dish_structure.achievedPointing[2]
    assert current_el == approx(stow_position, rel=TOLERANCE)

    LOGGER.info(f"{dish_manager} and {dish_structure} elevation: {current_el}")


@then(
    "dish_manager and dish_structure azimuth should remain in the same position"
)
def check_dish_manager_dish_structure_az_position(
    dish_manager,
    dish_structure,
    initial_az,
):
    # pylint: disable=missing-function-docstring
    # checking DISHMASTER az values
    current_az = dish_manager.achievedPointing[1]
    assert current_az == initial_az["az"]

    # checking DISHSTRUCTURE az values
    current_az = dish_structure.achievedPointing[1]
    assert current_az == initial_az["az"]

    LOGGER.info(f"{dish_manager} azimuth: {current_az}")


@then(parse("dish_manager pointingState should be {expected_pointing_state}"))
def check_pointing_state_after_stow(
    expected_pointing_state,
    dish_manager,
    pointing_state_event_store,
):
    # pylint: disable=missing-function-docstring
    pointing_state_event_store.wait_for_value(
        PointingState[expected_pointing_state], timeout=60
    )
    current_pointing_state = retrieve_attr_value(dish_manager, "pointingState")
    assert current_pointing_state == expected_pointing_state
    LOGGER.info(f"{dish_manager} pointingState: {current_pointing_state}")


@then(parse("dish_manager dish state should be {expected_dish_state}"))
def check_dish_state_after_stow(
    expected_dish_state,
    dish_manager,
):
    # pylint: disable=missing-function-docstring
    current_dish_state = retrieve_attr_value(dish_manager, "State")
    assert current_dish_state == expected_dish_state
    LOGGER.info(f"{dish_manager} State: {current_dish_state}")


@then(
    "dish_manager and dish_structure should report"
    " the same achieved elevation position"
)
def check_el_is_same_for_dish_and_ds(
    dish_manager,
    dish_structure,
):
    # pylint: disable=missing-function-docstring
    dish_manager_achieved_el = dish_manager.achievedPointing[2]
    dish_structure_achieved_el = dish_structure.achievedPointing[2]
    assert dish_manager_achieved_el == dish_structure_achieved_el

    LOGGER.info(
        f"{dish_manager} and {dish_structure} devices report the same achieved elevation position"
    )
