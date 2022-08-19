"""Test DS component manager"""
import logging

import pytest
import tango

from ska_mid_dish_manager.component_managers.ds_cm import DSComponentManager
from ska_mid_dish_manager.models.dish_enums import (
    DSOperatingMode,
    DSPowerState,
)

LOGGER = logging.getLogger(__name__)


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_ds_cm(component_state_store, ds_device_fqdn):
    """Stress test component updates"""
    device_proxy = tango.DeviceProxy(ds_device_fqdn)
    # Get into a known state
    device_proxy.Stow()

    com_man = DSComponentManager(
        ds_device_fqdn,
        LOGGER,
        component_state_callback=component_state_store,
    )
    com_man.start_communicating()
    component_state_store.wait_for_value("connection_state", "monitoring")
    device_proxy.SetStartupMode()
    component_state_store.wait_for_value(
        "operatingmode", DSOperatingMode.STARTUP
    )
    device_proxy.SetStandbyFPMode()
    component_state_store.wait_for_value(
        "operatingmode", DSOperatingMode.STANDBY_FP
    )
    component_state_store.wait_for_value("powerstate", DSPowerState.FULL_POWER)
    com_man.stop_communicating()
    component_state_store.wait_for_value("connection_state", "disconnected")
