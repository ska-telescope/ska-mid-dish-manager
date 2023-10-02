"""
Verify that dish lmc mode transitions

(R.LMC.SM.12, R.LMC.SM.1, R.LMC.SM.2, R.LMC.SM.6
R.LMC.SM.22 except MAINTENANCE, R.LMC.SM.13, R.LMC.SM.15, R.LMC.SM.16)

NOTE: In tests the enums with `-` is replace with `_` to handle both cases.
E.g FULL-POWER to FULL_POWER
"""

import logging

import pytest
import tango
from pytest_bdd import given, scenario, then, when
from pytest_bdd.parsers import parse
from utils import retrieve_attr_value

from ska_mid_dish_manager.models.dish_enums import SPFRxOperatingMode

LOGGER = logging.getLogger(__name__)


@pytest.mark.lmc
@scenario("XTP-15466.feature", "Test STANDBY-FP to OPERATE")
def test_fp_to_operate_mode_transition():
    # pylint: disable=missing-function-docstring
    pass


@given(parse("dish_manager dishMode reports {dish_mode}"))
def check_dish_manager_dish_mode(dish_mode, dish_manager, modes_helper):
    # pylint: disable=missing-function-docstring
    # convert dish mode to have underscore
    # for DishMode STANDBY_FP/LP enums in utils
    dish_mode = dish_mode.replace("-", "_")

    modes_helper.ensure_dish_manager_mode(dish_mode)
    current_dish_mode = retrieve_attr_value(dish_manager, "dishMode")
    LOGGER.info(f"{dish_manager} dishMode: {current_dish_mode}")


@given("dish has been configured for a frequency band")
def check_configured_band_and_spfrx_operating_mode(
    dish_manager, spfrx, spfrx_event_store, dish_freq_band_configuration
):
    # pylint: disable=missing-function-docstring
    dish_configured_band = retrieve_attr_value(dish_manager, "configuredBand")
    if dish_configured_band in ["NONE", "UNKNOWN"]:
        spfrx.subscribe_event(
            "operatingMode",
            tango.EventType.CHANGE_EVENT,
            spfrx_event_store,
        )
        dish_freq_band_configuration.go_to_band(2)
        spfrx_event_store.wait_for_value(SPFRxOperatingMode["DATA_CAPTURE"])

    spfrx_operating_mode = retrieve_attr_value(spfrx, "operatingMode")
    error_msg = "ConfigureBand command was not successful"
    assert spfrx_operating_mode.replace("-", "_") == "DATA_CAPTURE", error_msg
    LOGGER.info(f"{spfrx} operatingMode: {spfrx_operating_mode}")


@when(
    parse("I issue {command_name} on dish_manager"),
)
def desired_dish_mode(command_name, modes_helper, dish_manager):
    # pylint: disable=missing-function-docstring
    cmd_modes_map = {
        "SetStandbyLPMode": "STANDBY_LP",
        "SetStandbyFPMode": "STANDBY_FP",
        "SetOperateMode": "OPERATE",
        "SetStowMode": "STOW",
    }
    desired_dish_mode = cmd_modes_map[command_name]
    LOGGER.info(f"DishManager is {dish_manager.dishMode.name} going to mode {desired_dish_mode}")
    modes_helper.dish_manager_go_to_mode(desired_dish_mode)
    LOGGER.info(f"DishManager transitioned to {dish_manager.dishMode}")


@then(parse("dish_manager dishMode should report {desired_dish_mode}"))
def check_dish_mode_and_state(
    desired_dish_mode,
    dish_manager,
):
    # pylint: disable=missing-function-docstring
    # convert dish mode to have underscore
    # to match DishMode STANDBY_LP/FP enums
    current_dish_mode = retrieve_attr_value(dish_manager, "dishMode")
    assert current_dish_mode.replace("-", "_") == desired_dish_mode.replace("-", "_")
    LOGGER.info(f"{dish_manager} dishMode: {current_dish_mode}")


@then(
    parse(
        "dish_structure operatingMode and powerState should "
        "report {ds_operating_mode} and {ds_power_state}"
    )
)
def check_ds_operating_mode_and_power_state(
    ds_operating_mode,
    ds_power_state,
    dish_structure,
):
    # pylint: disable=missing-function-docstring
    current_operating_mode = retrieve_attr_value(dish_structure, "operatingMode")
    current_power_state = retrieve_attr_value(dish_structure, "powerState")
    assert current_operating_mode.replace("-", "_") == ds_operating_mode.replace("-", "_")
    assert current_power_state.replace("-", "_") == ds_power_state.replace("-", "_")
    LOGGER.info(
        f"{dish_structure} operatingMode: {current_operating_mode}"
        f", powerState: {current_power_state}"
    )


@then(
    parse(
        "spf operatingMode and powerState should report"
        " {spf_operating_mode} and {spf_power_state}"
    )
)
def check_spf_operating_mode_and_power_state(
    spf_operating_mode,
    spf_power_state,
    spf,
):
    # pylint: disable=missing-function-docstring
    current_operating_mode = retrieve_attr_value(spf, "operatingMode")
    current_power_state = retrieve_attr_value(spf, "powerState")
    assert current_operating_mode.replace("-", "_") == spf_operating_mode.replace("-", "_")
    assert current_power_state.replace("-", "_") == spf_power_state.replace("-", "_")
    LOGGER.info(
        f"{spf} operatingMode: {current_operating_mode}," f"powerState: {current_power_state}"
    )


@then(parse("spfrx operatingMode should report {spfrx_operating_mode}"))
def check_spfrx_operating_mode(
    spfrx_operating_mode,
    spfrx,
):
    # pylint: disable=missing-function-docstring
    current_operating_mode = retrieve_attr_value(spfrx, "operatingMode")
    assert current_operating_mode.replace("-", "_") == spfrx_operating_mode.replace("-", "_")
    LOGGER.info(f"{spfrx} operatingMode: {current_operating_mode}")
