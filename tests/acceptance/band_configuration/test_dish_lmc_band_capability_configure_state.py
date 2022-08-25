# flake8: noqa: E501
"""
Verify that:
    LMC reports Band_X Capability as CONFIGURE state if DSH is in CONFIGURE mode (L2-4700)
"""

import logging

import pytest
import tango
from pytest_bdd import given, scenario, then, when
from pytest_bdd.parsers import parse

from ska_mid_dish_manager.models.dish_enums import (
    CapabilityStates,
    DishMode,
    SPFCapabilityStates,
    SPFRxCapabilityStates,
)
from tests.utils_testing import retrieve_attr_value

LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def device_event_store():
    return {}


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.xfail(
    reason="DishManager DishMode never transitions through CONFIG\n"
    "DishManager capabilityState never transitions through CONFIGURING\n"
    "L2 requirement expects SPF CapabilityState to report OPERATE but ICD wants OPERATE-FULL\n"
    "L2 requirement expects DishManager CapabilityState to report CONFIGURE but ICD wants CONFIGURING"
)
@scenario(
    "../../features/XTP-6270.feature", "LMC Report DSH Capability Configure"
)
def test_dish_lmc_capability_state_reports_configure():
    """Test that dish lmc reports CONFIGURE capability state"""
    pass


@given(parse("dish_manager dishMode reports {dish_mode}"))
def check_dish_manager_dish_mode(dish_mode, dish_manager, modes_helper):
    # pylint: disable=missing-function-docstring
    # convert dish mode to have underscore
    # for DishMode STANDBY_FP enum in utils
    dish_mode = dish_mode.replace("-", "_")

    modes_helper.ensure_dish_manager_mode(dish_mode)
    current_dish_mode = retrieve_attr_value(dish_manager, "dishMode")
    LOGGER.info(f"{dish_manager} dishMode: {current_dish_mode}")


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
    attrs = ["dishMode", f"b{band_number}CapabilityState"]
    for attr in attrs:
        dish_manager.subscribe_event(
            attr,
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


@then(
    parse("dish_manager dishMode should have reported {expected_mode} briefly")
)
def check_dish_mode(
    dish_manager, expected_mode, dish_manager_event_store, device_event_store
):
    # pylint: disable=missing-function-docstring
    dish_evts = dish_manager_event_store.get_queue_values(timeout=60)
    # pass on the events for later use
    device_event_store["dish_manager"] = dish_evts

    dish_mode_evts = [
        evt_vals[1]
        for evt_vals in dish_evts
        if evt_vals[0].lower() == "dishmode"
    ]
    assert DishMode[expected_mode] in dish_mode_evts
    LOGGER.info(f"{dish_manager} dishMode reported: {expected_mode}")


@then(
    parse("spf b{band_number}CapabilityState should report {expected_state}")
)
def then_check_spf_capability_state(
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
    parse(
        "spfrx b{band_number}CapabilityState should report {operate} or {configure}"
    )
)
def check_spfrx_capability_state(
    band_number, operate, configure, spfrx, spfrx_event_store
):
    # pylint: disable=missing-function-docstring
    spfrx_capability_evts = [
        evt_vals[1]
        for evt_vals in spfrx_event_store.get_queue_values(timeout=60)
    ]

    assert (
        SPFRxCapabilityStates[operate] in spfrx_capability_evts
        or SPFRxCapabilityStates[configure] in spfrx_capability_evts
    )
    b_x_capability_state = retrieve_attr_value(
        spfrx, f"b{band_number}CapabilityState"
    )
    assert b_x_capability_state in [operate, configure]
    LOGGER.info(
        f"{spfrx} b{band_number}CapabilityState: {b_x_capability_state}"
    )


@then(
    parse(
        "dish_manager b{band_number}CapabilityState should have reported {expected_state} briefly"
    )
)
def check_dish_transient_capability_state(
    band_number,
    expected_state,
    dish_manager,
    dish_manager_event_store,
    device_event_store,
):
    # pylint: disable=missing-function-docstring
    dish_evts = dish_manager_event_store.get_queue_values(timeout=60)
    # combine the fresh events and the old one to check for values
    dish_evts = dish_evts + device_event_store["dish_manager"]

    capability_state_evts = [
        evt_vals[1]
        for evt_vals in dish_evts
        if evt_vals[0].lower() == f"b{band_number}capabilitystate"
    ]
    assert CapabilityStates[expected_state] in capability_state_evts

    LOGGER.info(
        f"{dish_manager} b{band_number}CapabilityState reported: {expected_state}"
    )
