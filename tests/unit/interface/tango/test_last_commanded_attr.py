"""Unit tests for setstandbylp command."""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    BandInFocus,
    DishMode,
    DSOperatingMode,
    IndexerPosition,
    SPFOperatingMode,
    SPFRxOperatingMode,
)


# pylint: disable=missing-function-docstring, protected-access
@pytest.mark.unit
@pytest.mark.forked
def test_set_operate_mode_succeeds_from_standbyfp_dish_mode(
    dish_manager_resources,
    event_store_class,
):
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]
    spfrx_cm = dish_manager_cm.sub_component_managers["SPFRX"]

    main_event_store = event_store_class()
    last_command_event_store = event_store_class()

    device_proxy.subscribe_event(
        "lastCommandedMode",
        tango.EventType.CHANGE_EVENT,
        last_command_event_store,
    )
    last_command_event_store.clear_queue()

    device_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )
    device_proxy.subscribe_event(
        "configuredBand",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )
    # Force dishManager dishMode to go to STANDBY_FP
    device_proxy.SetStandbyFPMode()
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_FP)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    main_event_store.wait_for_value(DishMode.STANDBY_FP)

    evts = last_command_event_store.wait_for_n_events(1)
    _, command_name = evts[0].attr_value.value
    assert command_name == "SetStandbyFPMode"

    changed_time, commanded_name = device_proxy.lastCommandedMode
    assert changed_time != "0.0"
    assert float(changed_time)
    assert commanded_name == "SetStandbyFPMode"

    # Transition DishManager to OPERATE mode with configuredBand not set
    device_proxy.SetOperateMode()
    # Set configuredBand and try again
    ds_cm._update_component_state(indexerposition=IndexerPosition.B1)
    spf_cm._update_component_state(bandinfocus=BandInFocus.B1)
    spfrx_cm._update_component_state(configuredband=Band.B1)
    # spfrx operating mode transitions to Data Capture after successful band configuration
    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.DATA_CAPTURE)
    main_event_store.wait_for_value(Band.B1, timeout=10)

    device_proxy.SetOperateMode()

    evts = last_command_event_store.wait_for_n_events(1)
    _, command_name = evts[0].attr_value.value
    assert command_name == "SetOperateMode"

    changed_time, commanded_name = device_proxy.lastCommandedMode
    assert float(changed_time)
    assert commanded_name == "SetOperateMode"
