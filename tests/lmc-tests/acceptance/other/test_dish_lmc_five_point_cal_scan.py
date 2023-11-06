"""
Verification test for the five point calibration scan
"""

import logging

import pytest
import tango
from pytest_bdd import given, scenario, then, when
from pytest_bdd.parsers import parse
from utils import retrieve_attr_value

LOGGER = logging.getLogger(__name__)


@pytest.mark.lmc
@scenario("XTP-28438.feature", "LMC Reports on the success of Tracking with programTrackTable")
def test_dish_lmc_succ_of_tracking_with_program_track_table():
    # pylint: disable=missing-function-docstring
    pass


@given(parse("dish_manager dishMode reports {dish_mode}"))
def check_dish_manager_dish_mode(dish_mode, dish_manager, modes_helper):
    # pylint: disable=missing-function-docstring
    modes_helper.ensure_dish_manager_mode(dish_mode)
    current_dish_mode = retrieve_attr_value(dish_manager, "dishMode")
    LOGGER.info(f"{dish_manager} dishMode: {current_dish_mode}")


@given(parse("dish_manager configuredBand reports {expected_band}"))
def check_dish_configured_band(expected_band, dish_manager):
    # pylint: disable=missing-function-docstring
    configured_band = retrieve_attr_value(dish_manager, "configuredBand")
    assert configured_band == expected_band
    LOGGER.info(f"{dish_manager} configuredBand: {configured_band}")


@given(("I write to programTrackTable on dish_manager"))
def update_program_track_table(dish_manager):
    # pylint: disable=missing-function-docstring
    desired_array = [5, 15, 30]
    dish_manager.programTrackTable = [5, 15, 30]
    assert dish_manager.programTrackTable() == desired_array


@when(("I issue Track on dish_manager"))
def issue_track_on_dish_manager(dish_manager, event_store):
    # pylint: disable=missing-function-docstring

    # event subscription on pointing state will be needed
    # event store should be scoped at module so that its
    # content are available for use in the next function

    dish_manager.Track()
    dish_manager.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )


@then(parse("pointingState should report {pointing_state}"))
def check_dish_manager_pointing_state_track(pointing_state, dish_manager, event_store):
    # pylint: disable=missing-function-docstring
    # for cases that the event may not arrive early just wait a bit
    desired_pointing_state = "Track"
    current_pointing_state = event_store.wait_for_value(pointing_state)
    assert current_pointing_state == desired_pointing_state
    LOGGER.info(f"{dish_manager} pointing state is: {current_pointing_state}")


@when(("I issue TrackStop on dish_manager"))
def desired_dish_mode_track_stop(dish_manager, modes_helper):
    # pylint: disable=missing-function-docstring
    desired_dish_mode = "TrackStop"
    dish_manager.TrackStop()
    modes_helper.dish_manager_go_to_mode(desired_dish_mode)


@then(parse("pointingState should report {pointing_state}"))
def check_dish_manager_pointing_state_track_stop(pointing_state, dish_manager, event_store):
    # pylint: disable=missing-function-docstring

    # again, we can use the event_store to wait for value

    current_pointing_state = retrieve_attr_value(dish_manager, "pointingState")
    assert current_pointing_state == pointing_state
    LOGGER.info(f"{dish_manager} pointing state is:: {current_pointing_state}")
