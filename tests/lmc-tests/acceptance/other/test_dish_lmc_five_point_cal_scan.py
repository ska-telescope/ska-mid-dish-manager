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


@given(parse("dish_manager dishMode reports OPERATE"))
def check_dish_manager_dish_mode(dish_manager, modes_helper):
    # pylint: disable=missing-function-docstring
    # convert dish mode to have underscore
    # for DishMode OPERATE enum in utils
    dish_mode = "OPERATE"
    modes_helper.ensure_dish_manager_mode(dish_mode)
    current_dish_mode = retrieve_attr_value(dish_manager, "dishMode")
    LOGGER.info(f"{dish_manager} dishMode: {current_dish_mode}")


@then(parse("dish_manager configuredBand reports B2"))
def check_dish_configured_band(dish_manager):
    # pylint: disable=missing-function-docstring
    configured_band = retrieve_attr_value(dish_manager, "configuredBand")
    assert configured_band == "B2"
    LOGGER.info(f"{dish_manager} configuredBand: {configured_band}")


@then(
    parse("I wrote to programTrackTable on dish_manager"),
)
def desired_dish_mode_program_track_table(dish_manager, modes_helper):
    # pylint: disable=missing-function-docstring
    desired_dish_mode = "programTrackTable"
    dish_manager.programTrackTable(5)
    assert dish_manager.programTrackTable() == 5

    modes_helper.dish_manager_go_to_mode(desired_dish_mode)


@when(
    parse("I call command Track on dish_manager"),
)
def desired_dish_mode_dm_command(modes_helper):
    # pylint: disable=missing-function-docstring
    desired_dish_mode = "Track"
    modes_helper.dish_manager_go_to_mode(desired_dish_mode)


@then(parse("pointingState should report Track"))
def check_dish_manager_pointing_state(dish_manager, event_store):
    # pylint: disable=missing-function-docstring
    # for cases that the event may not arrive early just wait a bit
    dish_manager.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    current_pointing_state = retrieve_attr_value(dish_manager, "pointingState")
    assert current_pointing_state.replace("-", "_") == "Track"
    LOGGER.info(f"{dish_manager} operatingMode: {current_pointing_state}")


@when(
    parse("I call command TrackStop on dish_manager"),
)
def desired_dish_mode_dm_command(modes_helper):
    # pylint: disable=missing-function-docstring
    desired_dish_mode = "TrackStop"
    modes_helper.dish_manager_go_to_mode(desired_dish_mode)


@then(parse("pointingState should report Ready"))
def check_dish_manager_pointing_state(dish_manager, event_store):
    # pylint: disable=missing-function-docstring
    # for cases that the event may not arrive early just wait a bit
    dish_manager.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    current_pointing_state = retrieve_attr_value(dish_manager, "pointingState")
    assert current_pointing_state.replace("-", "_") == "Ready"
    LOGGER.info(f"{dish_manager} operatingMode: {current_pointing_state}")
