# flake8: noqa: E501
"""
Verify that:
    LMC reports Band X Capability as OPERATE (L2-4699)
"""

import logging

import pytest
import tango
from pytest_bdd import given, scenario, then, when
from pytest_bdd.parsers import parse

from ska_mid_dish_manager.models.dish_enums import (
    CapabilityStates,
    SPFCapabilityStates,
    SPFRxCapabilityStates,
)
from tests.utils_testing import retrieve_attr_value

LOGGER = logging.getLogger(__name__)


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.xfail(
    reason="spf CapabilityState has one more enum (UNKNOWN) in simulator than the ICD\n"
    "L2 requirement expects DishManager CapabilityState to report OPERATE-FULL but ICD wants OPERATE\n"
)
@scenario(
    "../../features/XTP-6271.feature", "LMC Report DSH Capability Operate"
)
def test_band_capability_state_operate():
    # pylint: disable=missing-function-docstring
    pass


@given(parse("dish_manager dishMode reports {dish_mode}"))
def check_dish_manager_dish_mode(dish_mode, dish_manager, modes_helper):
    # pylint: disable=missing-function-docstring
    modes_helper.ensure_dish_manager_mode(dish_mode)
    current_dish_mode = retrieve_attr_value(dish_manager, "dishMode")
    LOGGER.info(f"{dish_manager} dishMode: {current_dish_mode}")


@given(parse("dish_structure operatingMode reports {operating_mode}"))
def check_dish_structure_operating_mode(operating_mode, dish_structure):
    # pylint: disable=missing-function-docstring
    current_operating_mode = retrieve_attr_value(
        dish_structure, "operatingMode"
    )
    assert current_operating_mode == operating_mode
    LOGGER.info(f"{dish_structure} operatingMode: {current_operating_mode}")


@when(parse("I issue ConfigureBand{band_number} on dish_manager"))
def configure_band(
    band_number,
    dish_freq_band_configuration,
    dish_manager,
    dish_manager_event_store,
    spf,
    spf_event_store,
    spfrx,
    spfrx_event_store,
):
    # pylint: disable=missing-function-docstring
    dish_manager.subscribe_event(
        f"b{band_number}CapabilityState",
        tango.EventType.CHANGE_EVENT,
        dish_manager_event_store,
    )

    band_number = 5 if band_number.startswith("5") else band_number
    spf.subscribe_event(
        f"b{band_number}CapabilityState",
        tango.EventType.CHANGE_EVENT,
        spf_event_store,
    )

    spfrx.subscribe_event(
        f"b{band_number}CapabilityState",
        tango.EventType.CHANGE_EVENT,
        spfrx_event_store,
    )

    dish_freq_band_configuration.go_to_band(band_number)


@then(parse("dish_structure indexerPosition should report {band_number}"))
def check_ds_indexer_position_is_not_moving(
    band_number,
    dish_structure,
):
    # pylint: disable=missing-function-docstring
    band_number = 5 if band_number.startswith("5") else band_number
    indexer_position = retrieve_attr_value(dish_structure, "indexerPosition")
    assert indexer_position == f"B{band_number}"
    LOGGER.info(f"{dish_structure} indexerPosition: {indexer_position}")


@then(
    parse("spf b{band_number}CapabilityState should report {expected_state}")
)
def check_spf_band_capability_state(
    band_number, expected_state, spf, spf_event_store
):
    # pylint: disable=missing-function-docstring
    # convert expected state to have underscore
    # for SPFCapabilityStates OPERATE_FULL enum
    expected_state = expected_state.replace("-", "_")

    spf_event_store.wait_for_value(
        SPFCapabilityStates[expected_state], timeout=60
    )
    band_number = 5 if band_number.startswith("5") else band_number
    b_x_capability_state = retrieve_attr_value(
        spf, f"b{band_number}CapabilityState"
    )
    assert b_x_capability_state == expected_state
    LOGGER.info(f"{spf} b{band_number}CapabilityState: {b_x_capability_state}")


@then(
    parse("spfrx b{band_number}CapabilityState should report {expected_state}")
)
def check_spfrx_capability_state(
    band_number, expected_state, spfrx, spfrx_event_store
):
    # pylint: disable=missing-function-docstring
    spfrx_event_store.wait_for_value(
        SPFRxCapabilityStates[expected_state], timeout=60
    )
    b_x_capability_state = retrieve_attr_value(
        spfrx, f"b{band_number}CapabilityState"
    )
    assert b_x_capability_state == expected_state
    LOGGER.info(
        f"{spfrx} b{band_number}CapabilityState: {b_x_capability_state}"
    )


@then(
    parse(
        "dish_manager b{band_number}CapabilityState should report {expected_state}"
    )
)
def check_dish_manager_band_capability_state(
    band_number,
    expected_state,
    dish_manager,
    dish_manager_event_store,
):
    # pylint: disable=missing-function-docstring
    # convert expected state to have underscore for enums in utils
    expected_state = expected_state.replace("-", "_")

    dish_manager_event_store.wait_for_value(
        CapabilityStates[expected_state], timeout=60
    )
    b_x_capability_state = retrieve_attr_value(
        dish_manager, f"b{band_number}CapabilityState"
    )
    assert b_x_capability_state == expected_state
    LOGGER.info(
        f"{dish_manager} b{band_number}CapabilityState: {b_x_capability_state}"
    )
