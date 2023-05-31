"""
Verify that dish lmc captures data in the configured band
"""

import logging

import pytest
import tango
from pytest_bdd import given, scenario, then
from pytest_bdd.parsers import parse
from utils import retrieve_attr_value

LOGGER = logging.getLogger(__name__)


@pytest.mark.acceptance
@scenario("XTP-14050.feature", "LMC does not capture data in STANDBY-LP mode")
def test_dish_lmc_does_not_capture_data_in_lp():
    # pylint: disable=missing-function-docstring
    pass


@pytest.mark.acceptance
@scenario(
    "XTP-15468.feature",
    "LMC does not capture data in STANDBY-FP mode with no band",
)
def test_dish_lmc_does_not_capture_data_in_fp_no_band(
    reset_receiver_devices, reset_ds_indexer_position
):
    # pylint: disable=missing-function-docstring
    pass


@pytest.mark.acceptance
@scenario("XTP-15469.feature", "LMC captures data in the configuredBand")
def test_dish_lmc_captures_data_in_the_configured_band():
    # pylint: disable=missing-function-docstring
    pass


@given(parse("dish_manager configuredBand is {band_number}"))
def dish_manager_configure_band(
    band_number,
    dish_freq_band_configuration,
):
    # pylint: disable=missing-function-docstring
    dish_freq_band_configuration.go_to_band(band_number)


@given("dish_manager has no configuredBand")
def dish_manager_has_no_configured_band(dish_manager):
    configured_band = retrieve_attr_value(dish_manager, "configuredBand")
    assert configured_band in ["NONE", "UNKNOWN"]


@given(parse("dish_manager reports {dish_mode}"))
def check_dish_manager_dish_mode(
    dish_mode,
    dish_manager,
    modes_helper,
):
    # pylint: disable=missing-function-docstring
    dish_mode = dish_mode.replace("-", "_")
    modes_helper.ensure_dish_manager_mode(dish_mode)
    current_dish_mode = retrieve_attr_value(dish_manager, "dishMode")
    LOGGER.info(f"{dish_manager} dishMode: {current_dish_mode}")


@then(parse("spfrx operatingMode should report {expected_operating_mode}"))
def check_spfrx_operating_mode(spfrx, event_store, expected_operating_mode):
    # pylint: disable=missing-function-docstring
    # for cases that the event may not arrive early just wait a bit
    spfrx.subscribe_event(
        f"operatingMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    spfrx_events = event_store.get_queue_values()
    assert spfrx_events

    current_operating_mode = retrieve_attr_value(spfrx, "operatingMode")
    assert current_operating_mode.replace("-", "_") == expected_operating_mode.replace("-", "_")
    LOGGER.info(f"{spfrx} operatingMode: {current_operating_mode}")


@then(
    parse(
        "dish_manager capturing and spfrx capturingData attributes should report {value}"
    )
)
def dish_manager_capturing_reports_spfrx_capturing_data(
    dish_manager, spfrx, value
):
    # pylint: disable=missing-function-docstring
    capturing = retrieve_attr_value(dish_manager, "capturing")
    capturing_data = retrieve_attr_value(spfrx, "capturingData")
    assert str(capturing) == str(capturing_data) == str(value)
    LOGGER.info(
        f"{dish_manager} capturing: {capturing}, {spfrx} capturingData: {capturing_data}"
    )
