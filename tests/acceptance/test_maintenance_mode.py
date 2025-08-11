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
from tests.utils import EventStore, setup_subscriptions


@pytest.mark.acceptance
@pytest.mark.forked
def test_maintenance_mode_cmds(
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

    subscriptions = []
    subscriptions.append(setup_subscriptions(dish_manager_proxy, {"dishMode": mode_event_store}))
    ds_attr_cb_mapping = {
        "dsccmdAuth": dsc_event_store,
        "operatingmode": dsc_auth_event_store,
    }
    subscriptions.append(setup_subscriptions(ds_device_proxy, ds_attr_cb_mapping))
    subscriptions.append(setup_subscriptions(spf_device_proxy, {"operatingmode": spf_event_store}))
    subscriptions.append(
        setup_subscriptions(spfrx_device_proxy, {"operatingmode": spfrx_event_store})
    )

    mode_event_store.clear_queue()
    dsc_auth_event_store.clear_queue()
    spf_event_store.clear_queue()
    spfrx_event_store.clear_queue()
    dsc_event_store.clear_queue()
    dish_manager_proxy.SetStowMode()

    dish_manager_proxy.SetMaintenanceMode()

    dsc_event_store.wait_for_value(DSOperatingMode.STOW, timeout=60)
    spfrx_event_store.wait_for_value(SPFRxOperatingMode.STANDBY, timeout=30)
    spf_event_store.wait_for_value(SPFOperatingMode.MAINTENANCE, timeout=30)
    mode_event_store.wait_for_value(DishMode.Maintenance, timeout=30)
    dsc_auth_event_store.wait_for_value(DscCmdAuthType.NO_AUTHORITHY, timeout=30)

    for subscription in subscriptions:
        subscription.remove()
