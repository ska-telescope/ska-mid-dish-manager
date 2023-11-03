"""
Need to add in a doc string relevent to this file
"""

import logging

import pytest
import tango
from pytest_bdd import given, scenario, then, when
from pytest_bdd.parsers import parse
from utils import retrieve_attr_value

LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="module", name="initial_mode")
def fixture_initial_dish_mode():
    # pylint: disable=missing-function-docstring
    return {"dishMode": None}


@pytest.fixture(scope="function")
def dm_event_store(event_store_class):
    # pylint: disable=missing-function-docstring
    return event_store_class()


@pytest.mark.lmc
@scenario("XTP-28438.feature", "LMC Reports on the success of Tracking with programTrackTable")
def test_dish_lmc_succ_of_tracking_with_program_track_table():
    # pylint: disable=missing-function-docstring
    pass


@given(parse("dish_manager dishMode reports {dish_mode}"))
def check_dish_manager_dish_mode(dish_mode, dish_manager, modes_helper):
    # pylint: disable=missing-function-docstring
    # convert dish mode to have underscore
    # for DishMode OPERATE enum in utils
    dish_mode = dish_mode.replace("-", "_")

    modes_helper.ensure_dish_manager_mode(dish_mode)
    current_dish_mode = retrieve_attr_value(dish_manager, "dishMode")
    LOGGER.info(f"{dish_manager} dishMode: {current_dish_mode}")


@then(parse("dish_manager configuredBand reports B{band_number}"))
def check_dish_configured_band(band_number, dish_manager):
    # pylint: disable=missing-function-docstring
    configured_band = retrieve_attr_value(dish_manager, "configuredBand")
    assert configured_band == f"B{band_number}"
    LOGGER.info(f"{dish_manager} configuredBand: {configured_band}")


@then(
    parse("I have issued programTrackTable on dish_manager"),
)
def desired_dish_mode_program_track_table(modes_helper):
    # pylint: disable=missing-function-docstring
    desired_dish_mode = "programTrackTable"
    modes_helper.dish_manager_go_to_mode(desired_dish_mode)


@when(
    parse("I call command {dm_command} on dish_manager"),
)
def desired_dish_mode_dm_command(dm_command, modes_helper):
    # pylint: disable=missing-function-docstring
    desired_dish_mode = dm_command
    modes_helper.dish_manager_go_to_mode(desired_dish_mode)


@then(parse("pointingState should report {expected_pointing_state}"))
def check_dish_manager_pointing_state(dish_manager, event_store, expected_pointing_state):
    # pylint: disable=missing-function-docstring
    # for cases that the event may not arrive early just wait a bit
    dish_manager.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    spfrx_events = event_store.get_queue_values()
    assert spfrx_events

    current_pointing_state = retrieve_attr_value(dish_manager, "pointingState")
    assert current_pointing_state.replace("-", "_") == expected_pointing_state.replace("-", "_")
    LOGGER.info(f"{dish_manager} operatingMode: {current_pointing_state}")
