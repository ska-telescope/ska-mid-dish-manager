"""
Verify that:
    LMC reports Band X Capability as OPERATE (L2-4699)
"""

import logging

import pytest
import tango
from pytest_bdd import given, scenario, then, when
from pytest_bdd.parsers import parse
from utils import retrieve_attr_value

from ska_mid_dish_manager.models.dish_enums import (
    CapabilityStates,
    SPFCapabilityStates,
    SPFRxCapabilityStates,
)

LOGGER = logging.getLogger(__name__)


@pytest.mark.lmc
@scenario("XTP-6271.feature", "LMC Reports DSH Capability Operate")
def test_band_capability_state_operate(reset_receiver_devices, reset_ds_indexer_position):
    # pylint: disable=missing-function-docstring
    pass


@given(parse("dish_manager dishMode reports {dish_mode} for band{band_number} configuration"))
def check_dish_manager_dish_mode(
    dish_mode,
    band_number,
    dish_manager,
    dish_manager_event_store,
    spf,
    spf_event_store,
    modes_helper,
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
    modes_helper.ensure_dish_manager_mode(dish_mode)
    current_dish_mode = retrieve_attr_value(dish_manager, "dishMode")
    LOGGER.info(f"{dish_manager} dishMode: {current_dish_mode}")


@given(parse("dish_structure operatingMode reports {operating_mode}"))
def check_dish_structure_operating_mode(operating_mode, dish_structure):
    # pylint: disable=missing-function-docstring
    current_operating_mode = retrieve_attr_value(dish_structure, "operatingMode")
    assert current_operating_mode == operating_mode
    LOGGER.info(f"{dish_structure} operatingMode: {current_operating_mode}")


@when(parse("I issue ConfigureBand{band_number} on dish_manager"))
def configure_band(
    band_number,
    dish_freq_band_configuration,
    spf,
    spfrx,
    dish_manager,
    spfrx_event_store,
):
    # pylint: disable=missing-function-docstring
    spfrx.subscribe_event(
        f"b{band_number}CapabilityState",
        tango.EventType.CHANGE_EVENT,
        spfrx_event_store,
    )
    dish_freq_band_configuration.go_to_band(band_number)

    dish_mode = retrieve_attr_value(dish_manager, "dishMode")
    if dish_mode == "STOW":
        spf.SetCapStateDegraded(1)


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


@then(parse("spf b{band_number}CapabilityState should report {expected_state}"))
def check_spf_band_capability_state(band_number, expected_state, spf, spf_event_store):
    # pylint: disable=missing-function-docstring
    # convert expected state to have underscore
    # for SPFCapabilityStates OPERATE_FULL enum
    expected_state = expected_state.replace("-", "_")

    spf_events = spf_event_store.get_queue_values(timeout=20)
    spf_cap_state_events = [
        evt_vals[1]
        for evt_vals in spf_events
        if evt_vals[1] == SPFCapabilityStates[expected_state]
    ]
    assert spf_cap_state_events

    band_number = 5 if band_number.startswith("5") else band_number
    b_x_capability_state = retrieve_attr_value(spf, f"b{band_number}CapabilityState")
    assert b_x_capability_state == expected_state
    LOGGER.info(f"{spf} b{band_number}CapabilityState: {b_x_capability_state}")


@then(parse("spfrx b{band_number}CapabilityState should report {expected_state}"))
def check_spfrx_capability_state(band_number, expected_state, spfrx, spfrx_event_store):
    # pylint: disable=missing-function-docstring
    spfrx_event_store.wait_for_value(SPFRxCapabilityStates[expected_state])
    b_x_capability_state = retrieve_attr_value(spfrx, f"b{band_number}CapabilityState")
    assert b_x_capability_state == expected_state
    LOGGER.info(f"{spfrx} b{band_number}CapabilityState: {b_x_capability_state}")


@then(parse("dish_manager b{band_number}CapabilityState should report {expected_state}"))
def check_dish_manager_band_capability_state(
    band_number,
    expected_state,
    dish_manager,
    dish_manager_event_store,
):
    # pylint: disable=missing-function-docstring
    # convert expected state to have underscore for enums in utils
    expected_state = expected_state.replace("-", "_")

    dm_events = dish_manager_event_store.get_queue_values()
    dm_cap_state_events = [
        evt_vals[1] for evt_vals in dm_events if evt_vals[1] == CapabilityStates[expected_state]
    ]
    assert dm_cap_state_events

    b_x_capability_state = retrieve_attr_value(dish_manager, f"b{band_number}CapabilityState")
    assert b_x_capability_state == expected_state
    LOGGER.info(f"{dish_manager} b{band_number}CapabilityState: {b_x_capability_state}")
