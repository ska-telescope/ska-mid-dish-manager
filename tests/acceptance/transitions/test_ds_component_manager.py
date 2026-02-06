"""Test DS component manager."""

import logging
from threading import Lock

import pytest
import tango

from ska_mid_dish_manager.component_managers.ds_cm import DSComponentManager
from ska_mid_dish_manager.models.dish_enums import DSOperatingMode, DSPowerState

LOGGER = logging.getLogger(__name__)


# classifying as fast to balance the total run time across parallel jobs
@pytest.mark.fast
@pytest.mark.acceptance
def test_ds_cm(monitor_tango_servers, component_state_store, ds_device_fqdn):
    """Stress test component updates."""
    state_update_lock = Lock()
    com_man = DSComponentManager(
        ds_device_fqdn,
        LOGGER,
        state_update_lock,
        component_state_callback=component_state_store,
    )
    try:
        com_man.start_communicating()

        device_proxy = tango.DeviceProxy(ds_device_fqdn)

        device_proxy.SetStandbyMode()
        component_state_store.wait_for_value("operatingmode", DSOperatingMode.STANDBY)
        component_state_store.wait_for_value("powerstate", DSPowerState.LOW_POWER)

        device_proxy.SetPointMode()
        component_state_store.wait_for_value("powerstate", DSPowerState.FULL_POWER)
        component_state_store.wait_for_value("operatingmode", DSOperatingMode.POINT)
    finally:
        com_man.stop_communicating()
