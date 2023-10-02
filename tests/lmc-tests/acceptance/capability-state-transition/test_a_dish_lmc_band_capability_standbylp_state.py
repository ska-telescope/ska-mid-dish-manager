"""
Verify that LMC reports Band_X Capability as STANDBY state if DSH is in STANDBY-LP mode (L2-4697)
"""
import logging

import pytest
import tango
from pytest_bdd import given, scenario, then
from pytest_bdd.parsers import parse
from utils import retrieve_attr_value

from ska_mid_dish_manager.models.dish_enums import (
    CapabilityStates,
    SPFCapabilityStates,
    SPFRxCapabilityStates,
)

LOGGER = logging.getLogger(__name__)


@pytest.mark.lmc
@scenario(
    "XTP-6269.feature",
    "LMC Reports DSH Capability Standby in LP Mode",
)
def test_dish_manager_capability_state_reports_standby_in_lp_mode():
    """Test that dish lmc reports STANDBY capability state"""
    pass


@given(parse("dish_manager dishMode reports {dish_mode}"))
def check_dish_manager_dish_mode(dish_mode, dish_manager, modes_helper):
    # pylint: disable=missing-function-docstring
    # convert dish mode to have underscore
    # for DishMode STANDBY_LP enum in utils
    dish_mode = dish_mode.replace("-", "_")

    modes_helper.ensure_dish_manager_mode(dish_mode)
    current_dish_mode = retrieve_attr_value(dish_manager, "dishMode")
    LOGGER.info(f"{dish_manager} dishMode: {current_dish_mode}")


@given(parse("spfrx b{band_number}CapabilityState reports {expected_state}"))
def check_spfrx_capability_state(band_number, expected_state, spfrx, spfrx_event_store):
    # pylint: disable=missing-function-docstring
    spfrx.subscribe_event(
        f"b{band_number}CapabilityState",
        tango.EventType.CHANGE_EVENT,
        spfrx_event_store,
    )
    spfrx_event_store.wait_for_value(SPFRxCapabilityStates[expected_state], timeout=10)
    b_x_capability_state = retrieve_attr_value(spfrx, f"b{band_number}CapabilityState")
    assert b_x_capability_state == expected_state
    LOGGER.info(f"{spfrx} b{band_number}CapabilityState: {b_x_capability_state}")


@given(parse("spf b{band_number}CapabilityState reports {expected_state}"))
def check_spf_capability_state(
    band_number,
    expected_state,
    spf,
    spf_event_store,
):
    # pylint: disable=missing-function-docstring
    spf.subscribe_event(
        f"b{band_number}CapabilityState",
        tango.EventType.CHANGE_EVENT,
        spf_event_store,
    )
    spf_event_store.wait_for_value(SPFCapabilityStates[expected_state], timeout=10)
    band_number = 5 if band_number.startswith("5") else band_number
    b_x_capability_state = retrieve_attr_value(spf, f"b{band_number}CapabilityState")
    assert b_x_capability_state == expected_state
    LOGGER.info(f"{spf} b{band_number}CapabilityState: {b_x_capability_state}")


@then(parse("dish_manager b{band_number}CapabilityState should report {expected_state}"))
def check_dish_capability_state(
    band_number, expected_state, dish_manager_event_store, dish_manager
):
    # pylint: disable=missing-function-docstring
    dish_manager.subscribe_event(
        f"b{band_number}CapabilityState",
        tango.EventType.CHANGE_EVENT,
        dish_manager_event_store,
    )
    b_x_capability_state = retrieve_attr_value(dish_manager, f"b{band_number}CapabilityState")
    dish_manager_event_store.wait_for_value(CapabilityStates[expected_state], timeout=10)
    assert b_x_capability_state == expected_state
    LOGGER.info(f"{dish_manager} b{band_number}CapabilityState: {b_x_capability_state}")
