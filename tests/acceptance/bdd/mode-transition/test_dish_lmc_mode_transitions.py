# flake8: noqa: E501
"""
Verify that dish lmc mode transitions

(R.LMC.SM.12, R.LMC.SM.1, R.LMC.SM.2, R.LMC.SM.6
R.LMC.SM.22 except MAINTENANCE, R.LMC.SM.13, R.LMC.SM.15, R.LMC.SM.16)
"""

import logging

import pytest
from pytest_bdd import given, scenario, then, when
from pytest_bdd.parsers import parse

from ska_mid_dish_manager.devices.test_devices.utils import retrieve_attr_value

LOGGER = logging.getLogger(__name__)


@pytest.mark.bdd
@pytest.mark.SKA_mid
@pytest.mark.acceptance
# @pytest.mark.xfail(
#     reason="Dish state reports DISABLE instead of STANDBY in STANDBY_LP-SetStowMode-DISABLE-STOW-LOW-POWER-STANDBY-LP-LOW-POWER-STANDBY\n"
#     "Dish state reports STANDBY instead of ON in STANDBY_FP-SetOperateMode-ON-POINT-FULL-POWER-OPERATE-FULL-POWER-DATA-CAPTURE\n"
#     "SPFRx operating mode reports STANDBY instead of DATA-CAPTURE in STANDBY-LP-SetStandbyFPMode-STANDBY-STANDBY-FP-FULL-POWER-OPERATE-FULL-POWER-DATA-CAPTURE"
# )
@scenario("../../features/XTP-813.feature", "Test dish lmc mode transitions")
def test_mode_transitions():
    # pylint: disable=missing-function-docstring
    pass


@given(parse("dish_manager dishMode reports {dish_mode}"))
def check_dish_manager_dish_mode(dish_mode, dish_manager, modes_helper):
    # pylint: disable=missing-function-docstring
    modes_helper.ensure_dish_manager_mode(dish_mode)
    current_dish_mode = retrieve_attr_value(dish_manager, "dishMode")
    LOGGER.info(f"{dish_manager} dishMode: {current_dish_mode}")


@when(
    parse("I issue {command_name} on dish_manager"),
    target_fixture="desired_dish_mode",
)
def desired_dish_mode(command_name, modes_helper):
    # pylint: disable=missing-function-docstring
    cmd_modes_map = {
        "SetStandbyLPMode": "STANDBY_LP",
        "SetStandbyFPMode": "STANDBY_FP",
        "SetOperateMode": "OPERATE",
        "SetStowMode": "STOW",
    }
    desired_dish_mode = cmd_modes_map[command_name]
    modes_helper.dish_manager_go_to_mode(desired_dish_mode)
    return desired_dish_mode


@then(
    parse(
        "dish_manager dishMode and state should report"
        " desired_dish_mode and {dish_state}"
    )
)
def check_dish_mode_and_state(
    desired_dish_mode,
    dish_state,
    dish_manager,
):
    # pylint: disable=missing-function-docstring
    current_dish_mode = retrieve_attr_value(dish_manager, "dishMode")
    current_dish_state = retrieve_attr_value(dish_manager, "State")
    assert current_dish_mode == desired_dish_mode
    assert current_dish_state == dish_state
    LOGGER.info(
        f"{dish_manager} dishMode: {current_dish_mode}, "
        f"State: {current_dish_state}"
    )


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
    current_operating_mode = retrieve_attr_value(
        dish_structure, "operatingMode"
    )
    current_power_state = retrieve_attr_value(dish_structure, "powerState")
    assert current_operating_mode == ds_operating_mode
    assert current_power_state == ds_power_state
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
    assert current_operating_mode == spf_operating_mode
    assert current_power_state == spf_power_state
    LOGGER.info(
        f"{spf} operatingMode: {current_operating_mode},"
        f"powerState: {current_power_state}"
    )


@then(parse("spfrx operatingMode should report {spfrx_operating_mode}"))
def check_spfrx_operating_mode(
    spfrx_operating_mode,
    spfrx,
):
    # pylint: disable=missing-function-docstring
    current_operating_mode = retrieve_attr_value(spfrx, "operatingMode")
    assert current_operating_mode == spfrx_operating_mode
    LOGGER.info(f"{spfrx} operatingMode: {current_operating_mode}")
