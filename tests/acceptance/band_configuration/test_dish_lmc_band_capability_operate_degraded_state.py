# flake8: noqa: E501
"""
Verify that LMC reports Band X Capability as OPERATE-DEGRADED (L2-4698)
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


@pytest.mark.xfail(
    reason="spf CapabilityState never transitions through 'OPERATE-DEGRADED'\n"
    "spf CapabilityState has one more enum (UNKNOWN) in simulator than the ICD\n"
    "dish manager CapabilityState never transitions through 'OPERATE-DEGRADED'\n"
)
@scenario(
    "../../features/XTP-6439.feature",
    "LMC Report DSH Capability Operate Degraded",
)
def test_band_capability_state_operate_degraded():
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
    spfrx,
    spf,
    dish_manager_event_store,
    spfrx_event_store,
    spf_event_store,
):
    # pylint: disable=missing-function-docstring
    dish_manager.subscribe_event(
        f"b{band_number}CapabilityState",
        tango.EventType.CHANGE_EVENT,
        dish_manager_event_store,
    )

    spfrx.subscribe_event(
        f"b{band_number}CapabilityState",
        tango.EventType.CHANGE_EVENT,
        spfrx_event_store,
    )

    band_number = 5 if band_number.startswith("5") else band_number
    spf.subscribe_event(
        f"b{band_number}CapabilityState",
        tango.EventType.CHANGE_EVENT,
        spf_event_store,
    )

    dish_freq_band_configuration.go_to_band(band_number)


@then(parse("dish_structure indexerPosition should report {band_number}"))
def check_ds_indexer_position_is_not_moving(
    band_number,
    dish_structure,
):
    # pylint: disable=missing-function-docstring
    # B5a and B5b are all returned as B5 for indexer_position
    band_number = 5 if band_number.startswith("5") else band_number
    indexer_position = retrieve_attr_value(dish_structure, "indexerPosition")
    assert indexer_position == f"B{band_number}"
    LOGGER.info(f"{dish_structure} indexerPosition: {indexer_position}")


@then(
    parse(
        "spf b{band_number}CapabilityState should have reported {expected_state} briefly"
    )
)
def check_spf_band_capability_transient_state(
    band_number, expected_state, spf, spf_event_store
):
    # pylint: disable=missing-function-docstring
    # convert expected state to have underscore
    # for SPFCapabilityStates OPERATE_DEGRADED enum
    expected_state = expected_state.replace("-", "_")

    spf_event_store.wait_for_value(
        SPFCapabilityStates[expected_state], timeout=60
    )
    band_number = 5 if band_number.startswith("5") else band_number
    LOGGER.info(
        f"{spf} b{band_number}CapabilityState reported: {expected_state}"
    )


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
        "dish_manager b{band_number}CapabilityState should have reported {expected_state} briefly"
    )
)
def check_dish_manager_band_capability_transient_state(
    band_number, expected_state, dish_manager_event_store, dish_manager
):
    # pylint: disable=missing-function-docstring
    # convert expected state to have underscore
    # for CapabilityStates OPERATE_DEGRADED enum
    expected_state = expected_state.replace("-", "_")

    dish_manager_event_store.wait_for_value(
        CapabilityStates[expected_state], timeout=60
    )
    LOGGER.info(
        f"{dish_manager} b{band_number}CapabilityState reported: {expected_state}"
    )
