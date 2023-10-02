"""
Verify that dish transitions to CONFIG from STANDBY_FP, STOW and OPERATE
(R.LMC.SM.14, R.LMC.SM.1, R.LMC.SM.2, R.LMC.SM.6)
"""

import logging

import pytest
import tango
from pytest_bdd import given, scenario, then, when
from pytest_bdd.parsers import parse
from utils import retrieve_attr_value

from ska_mid_dish_manager.models.dish_enums import DishMode

LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="module", name="initial_mode")
def fixture_initial_dish_mode():
    # pylint: disable=missing-function-docstring
    return {"dishMode": None}


@pytest.mark.lmc
@scenario("XTP-5703.feature", "Test dish lmc band selection")
def test_band_selection(monitor_tango_servers, reset_receiver_devices, reset_ds_indexer_position):
    # pylint: disable=missing-function-docstring
    pass


@given(parse("dish_manager dishMode reports {dish_mode}"))
def dish_reports_allowed_dish_mode(
    dish_mode,
    dish_manager,
    dish_manager_event_store,
    modes_helper,
    initial_mode,
):
    # pylint: disable=missing-function-docstring
    # convert dish mode to have underscore for enums in utils
    dish_manager.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_manager_event_store,
    )
    dish_mode = dish_mode.replace("-", "_")

    modes_helper.ensure_dish_manager_mode(dish_mode)
    current_dish_mode = retrieve_attr_value(dish_manager, "dishMode")
    LOGGER.info(f"{dish_manager} initial dishMode: {current_dish_mode}")
    # store starting dishMode for later use
    initial_mode["dishMode"] = current_dish_mode


@when(parse("I issue ConfigureBand{band_number} on dish_manager"))
def configure_band(
    band_number,
    dish_freq_band_configuration,
):
    # pylint: disable=missing-function-docstring
    dish_freq_band_configuration.go_to_band(band_number)


@then(parse("dish_manager dishMode should report {transient_mode} briefly"))
def check_dish_mode_reports_config(transient_mode, dish_manager, dish_manager_event_store):
    # pylint: disable=missing-function-docstring
    # convert dish mode to have underscore for enums in utils
    transient_mode = transient_mode.replace("-", "_")

    dish_manager_event_store.wait_for_value(DishMode[transient_mode], timeout=10)
    LOGGER.info(f"{dish_manager} dishMode reported: {transient_mode}")


@then(parse("dish_structure indexerPosition should report {band_number}"))
def check_ds_indexer_position_is_not_moving(band_number, dish_structure):
    # pylint: disable=missing-function-docstring
    # B5a and B5b are all returned as B5 for indexer_position
    band_number = 5 if band_number.startswith("5") else band_number
    indexer_position = retrieve_attr_value(dish_structure, "indexerPosition")
    assert indexer_position == f"B{band_number}"
    LOGGER.info(f"{dish_structure} indexerPosition: {indexer_position}")


@then(parse("spf bandInFocus should report {band_number}"))
def check_spf_band_in_focus(band_number, spf):
    # pylint: disable=missing-function-docstring
    # B5a and B5b are all returned as B5 for indexer_position
    band_number = 5 if band_number.startswith("5") else band_number
    band_in_focus = retrieve_attr_value(spf, "bandInFocus")
    assert band_in_focus == f"B{band_number}"
    LOGGER.info(f"{spf} bandInFocus: {band_in_focus}")


@then(parse("spfrx operatingMode should report {expected_mode}"))
def check_spfrx_operating_mode(expected_mode, spfrx):
    # pylint: disable=missing-function-docstring
    operating_mode = retrieve_attr_value(spfrx, "operatingMode")
    assert operating_mode.replace("-", "_") == expected_mode.replace("-", "_")
    LOGGER.info(f"{spfrx} operatingMode: {operating_mode}")


@then(parse("spfrx configuredBand should report {band_number}"))
def check_spfrx_configured_band(band_number, spfrx):
    # pylint: disable=missing-function-docstring
    configured_band = retrieve_attr_value(spfrx, "configuredBand")
    assert configured_band == f"B{band_number}"
    LOGGER.info(f"{spfrx} configuredBand: {configured_band}")


@then(parse("dish_manager configuredBand should report {band_number}"))
def check_dish_configured_band(band_number, dish_manager):
    # pylint: disable=missing-function-docstring
    configured_band = retrieve_attr_value(dish_manager, "configuredBand")
    assert configured_band == f"B{band_number}"
    LOGGER.info(f"{dish_manager} configuredBand: {configured_band}")


@then("dish_manager should report its initial dishMode")
def check_dish_mode_reports_initial_mode(dish_manager, initial_mode):
    # pylint: disable=missing-function-docstring
    dish_mode = retrieve_attr_value(dish_manager, "dishMode")
    assert dish_mode == initial_mode["dishMode"]
    LOGGER.info(f"{dish_manager} dishMode: {dish_mode}")
