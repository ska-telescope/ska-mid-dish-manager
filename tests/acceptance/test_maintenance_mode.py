"""Test Maintenance mode."""

from typing import Any

import pytest
import tango
from tango import DeviceProxy

from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DscCmdAuthType,
    SPFOperatingMode,
    SPFRxOperatingMode,
)


@pytest.mark.acceptance
@pytest.mark.forked
def test_maintanince_mode_cmds(
    event_store_class: Any,
    dish_manager_proxy: DeviceProxy,
    ds_device_proxy: DeviceProxy,
    spf_device_proxy: DeviceProxy,
    spfrx_device_proxy: DeviceProxy,
) -> None:
    """Test the behaviour of Maintenance mode."""
    mode_event_store = event_store_class()
    dsc_auth_event_store = event_store_class()
    spf_event_store = event_store_class()
    spfrx_event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        mode_event_store,
    )
    ds_device_proxy.subscribe_event(
        "dscCMDAuth",
        tango.EventType.CHANGE_EVENT,
        dsc_auth_event_store,
    )
    spf_device_proxy.subscribe_event(
        "operatingmode",
        tango.EventType.CHANGE_EVENT,
        spf_event_store,
    )
    spfrx_device_proxy.subscribe_event(
        "operatingmode",
        tango.EventType.CHANGE_EVENT,
        spfrx_event_store,
    )
    mode_event_store.clear_queue()
    dsc_auth_event_store.clear_queue()
    spf_device_proxy.clear_queue()
    spfrx_device_proxy.clear_queue()
    dish_manager_proxy.SetMaintenance()
    spf_event_store.wait_for_value(SPFOperatingMode.MAINTENANCE, timeout=30)
    spfrx_event_store.wait_for_value(SPFRxOperatingMode.STANDBY, timeout=30)
    mode_event_store.wait_for_value(DishMode.Maintenance, timeout=30)
    dsc_auth_event_store.wait_for_value(DscCmdAuthType.NO_AUTHORITHY, timeout=30)
