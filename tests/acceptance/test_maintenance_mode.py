"""Test Maintenance mode."""

import pytest
from tango import DeviceProxy

from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DscCmdAuthType,
    DSOperatingMode,
    SPFOperatingMode,
    SPFRxOperatingMode,
)
from tests.utils import EventStore, remove_subscriptions, setup_subscriptions


@pytest.mark.acceptance
@pytest.mark.forked
def test_maintenance_mode_cmds(
    reset_dish_to_standby: any,
    event_store_class: EventStore,
    dish_manager_proxy: DeviceProxy,
    ds_device_proxy: DeviceProxy,
    spf_device_proxy: DeviceProxy,
    spfrx_device_proxy: DeviceProxy,
) -> None:
    """Test the behaviour of Maintenance mode."""
    mode_event_store = event_store_class()
    dsc_event_store = event_store_class()
    dsc_auth_event_store = event_store_class()
    spf_event_store = event_store_class()
    spfrx_event_store = event_store_class()

    subscriptions = {}
    subscriptions.update(setup_subscriptions(spf_device_proxy, {"operatingMode": spf_event_store}))
    subscriptions.update(
        setup_subscriptions(spfrx_device_proxy, {"operatingMode": spfrx_event_store})
    )
    ds_attr_cb_mapping = {
        "dscCmdAuth": dsc_auth_event_store,
        "operatingMode": dsc_event_store,
    }
    subscriptions.update(setup_subscriptions(ds_device_proxy, ds_attr_cb_mapping))
    subscriptions.update(setup_subscriptions(dish_manager_proxy, {"dishMode": mode_event_store}))

    dish_manager_proxy.SetMaintenanceMode()

    dsc_event_store.wait_for_value(DSOperatingMode.STOW, timeout=120)
    spfrx_event_store.wait_for_value(SPFRxOperatingMode.STANDBY, timeout=30)
    spf_event_store.wait_for_value(SPFOperatingMode.MAINTENANCE, timeout=30)
    mode_event_store.wait_for_value(DishMode.MAINTENANCE, timeout=30)
    dsc_auth_event_store.wait_for_value(DscCmdAuthType.NO_AUTHORITY, timeout=30)

    remove_subscriptions(subscriptions)
