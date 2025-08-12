"""Test Maintenance mode."""

import pytest
from tango import DeviceProxy

from ska_mid_dish_manager.component_managers.device_proxy_factory import DeviceProxyManager
from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DscCmdAuthType,
    DSOperatingMode,
    SPFOperatingMode,
    SPFRxOperatingMode,
)
from tests.utils import EventStore, remove_subscriptions, setup_subscriptions

REQUESTED_AZIMUTH_VALUE = 100.0
REQUESTED_ELEVATION_VALUE = 60.0


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


@pytest.mark.acceptance
@pytest.mark.forked
def test_power_cycle_in_maintenance_mode(
    reset_dish_to_standby: any,
    event_store_class: EventStore,
    dish_manager_proxy: DeviceProxy,
) -> None:
    # Put dish into maintenance mode
    mode_event_store = event_store_class()
    buildstate_event_store = event_store_class()
    attr_cb_mapping = {
        "dishMode": mode_event_store,
        "buildState": buildstate_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)
    dish_manager_proxy.SetMaintenanceMode()
    mode_event_store.wait_for_value(DishMode.MAINTENANCE, timeout=120)

    # Restart the dish manager to simulate a power cycle
    dp_manager = DeviceProxyManager()
    # restart the sub-component device
    admin_device_proxy = dp_manager(dish_manager_proxy.adm_name())
    mode_event_store.clear_queue()
    admin_device_proxy.RestartServer()

    # Use the build state update to indicate when the dish manager is back
    buildstate_event_store.clear_queue()
    buildstate_event_store.wait_for_n_events(1, timeout=30)

    assert dish_manager_proxy.dishMode == DishMode.MAINTENANCE

    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
@pytest.mark.forked
def test_exiting_maintenance_mode_when_ds_on_stow(
    event_store_class: EventStore,
    dish_manager_proxy: DeviceProxy,
    ds_device_proxy: DeviceProxy,
) -> None:
    # Put dish into maintenance mode
    mode_event_store = event_store_class()
    dsc_event_store = event_store_class()
    attr_cb_mapping = {
        "dishMode": mode_event_store,
        "operatingMode": dsc_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)
    dish_manager_proxy.SetMaintenanceMode()
    mode_event_store.wait_for_value(DishMode.MAINTENANCE, timeout=120)
    dish_manager_proxy.SetStowMode()
    dsc_event_store.wait_for_value(DSOperatingMode.STOW, timeout=120)

    assert dish_manager_proxy.dishMode == DishMode.STOW

    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
@pytest.mark.forked
def test_exiting_maintenance_mode_when_ds_not_on_stow(
    event_store_class: EventStore,
    dish_manager_proxy: DeviceProxy,
    ds_device_proxy: DeviceProxy,
) -> None:
    # Put dish into maintenance mode
    mode_event_store = event_store_class()
    dsc_event_store = event_store_class()
    attr_cb_mapping = {
        "dishMode": mode_event_store,
        "operatingMode": dsc_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)
    dish_manager_proxy.SetMaintenanceMode()
    mode_event_store.wait_for_value(DishMode.MAINTENANCE, timeout=120)

    ds_device_proxy.unstow()
    dsc_event_store.wait_for_value(DSOperatingMode.STANDBY_FP, timeout=120)
    ds_device_proxy.slew([REQUESTED_AZIMUTH_VALUE, REQUESTED_ELEVATION_VALUE])
    dsc_event_store.wait_for_value(DSOperatingMode.POINT, timeout=30)
    dish_manager_proxy.SetStowMode()
    dsc_event_store.wait_for_value(DSOperatingMode.STOW, timeout=120)
    mode_event_store.wait_for_value(DishMode.UNKNOWN, timeout=30)

    assert dish_manager_proxy.dishMode == DishMode.STOW

    remove_subscriptions(subscriptions)
