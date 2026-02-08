"""Test Maintenance mode."""

import time

import pytest
from tango import DevFailed, DeviceProxy

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


@pytest.mark.movement
@pytest.mark.acceptance
def test_maintenance_mode_cmd(
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
    status_event_store = event_store_class()

    subscriptions = {}
    subscriptions.update(setup_subscriptions(spf_device_proxy, {"operatingMode": spf_event_store}))
    subscriptions.update(
        setup_subscriptions(spfrx_device_proxy, {"operatingMode": spfrx_event_store})
    )
    ds_attr_cb_mapping = {
        "dscCmdAuth": dsc_auth_event_store,
        "operatingMode": dsc_event_store,
    }
    dm_attr_cb_mapping = {
        "dishMode": mode_event_store,
        "Status": status_event_store,
    }
    subscriptions.update(setup_subscriptions(ds_device_proxy, ds_attr_cb_mapping))
    subscriptions.update(setup_subscriptions(dish_manager_proxy, dm_attr_cb_mapping))

    dish_manager_proxy.SetMaintenanceMode()

    mode_event_store.wait_for_value(DishMode.STOW, timeout=120)
    spfrx_event_store.wait_for_value(SPFRxOperatingMode.STANDBY, timeout=30)
    spf_event_store.wait_for_value(SPFOperatingMode.MAINTENANCE, timeout=30)
    mode_event_store.wait_for_value(DishMode.MAINTENANCE, timeout=30)
    dsc_auth_event_store.wait_for_value(DscCmdAuthType.NO_AUTHORITY, timeout=30)

    expected_progress_updates = [
        "Fanned out commands: DS.Stow, SPFRX.SetStandbyMode, SPF.SetMaintenanceMode",
        "Awaiting DS operatingmode change to STOW",
        "Awaiting SPFRX operatingmode change to STANDBY",
        "Awaiting SPF operatingmode change to MAINTENANCE",
        "Awaiting dishmode change to STOW",
        "SetMaintenanceMode completed",
    ]
    events = status_event_store.get_queue_events()
    events_string = "".join([str(event.attr_value.value) for event in events])
    # Check that all the expected progress messages appeared
    for message in expected_progress_updates:
        assert message in events_string

    remove_subscriptions(subscriptions)


@pytest.mark.movement
@pytest.mark.acceptance
def test_power_cycle_in_maintenance_mode(
    event_store_class: EventStore,
    dish_manager_proxy: DeviceProxy,
) -> None:
    # Put dish into maintenance mode
    mode_event_store = event_store_class()
    subscriptions = setup_subscriptions(
        dish_manager_proxy,
        {
            "dishMode": mode_event_store,
        },
    )
    dish_manager_proxy.SetMaintenanceMode()
    mode_event_store.wait_for_value(DishMode.MAINTENANCE, timeout=120)

    # Restart the dish manager to simulate a power cycle
    dp_manager = DeviceProxyManager()
    # restart the sub-component device
    admin_device_proxy = dp_manager(dish_manager_proxy.adm_name())
    admin_device_proxy.RestartServer()

    # Restarting the device server is not instantaneous, so we wait for a bit
    time.sleep(2)

    try:
        dp_manager.wait_for_device(dish_manager_proxy)
    except DevFailed:
        pass

    assert dish_manager_proxy.dishMode == DishMode.MAINTENANCE

    remove_subscriptions(subscriptions)


@pytest.mark.movement
@pytest.mark.acceptance
def test_exiting_maintenance_mode_when_ds_on_stow(
    event_store_class: EventStore,
    dish_manager_proxy: DeviceProxy,
    ds_device_proxy: DeviceProxy,
) -> None:
    # Put dish into maintenance mode
    mode_event_store = event_store_class()
    dsc_event_store = event_store_class()
    dsc_auth_event_store = event_store_class()
    ds_attr_cb_mapping = {
        "dscCmdAuth": dsc_auth_event_store,
        "operatingMode": dsc_event_store,
    }
    subscriptions = {}
    subscriptions.update(setup_subscriptions(dish_manager_proxy, {"dishMode": mode_event_store}))
    subscriptions.update(setup_subscriptions(ds_device_proxy, ds_attr_cb_mapping))
    dish_manager_proxy.SetMaintenanceMode()
    mode_event_store.wait_for_value(DishMode.MAINTENANCE, timeout=120)
    # Maintenance mode releases DSC authority, so increase client request timeout to 15 seconds
    # so that we don't time out while waiting for the DS horn when taking authority back.
    # Since Stow is not submitted as a task on DSManager this command will block the proxy.
    dish_manager_proxy.set_timeout_millis(15000)
    dish_manager_proxy.SetStowMode()
    dsc_event_store.wait_for_value(DSOperatingMode.STOW, timeout=120)
    dish_manager_proxy.set_timeout_millis(5000)

    assert dish_manager_proxy.dishMode == DishMode.STOW

    remove_subscriptions(subscriptions)


@pytest.mark.movement
@pytest.mark.acceptance
def test_exiting_maintenance_mode_when_ds_not_on_stow(
    event_store_class: EventStore,
    dish_manager_proxy: DeviceProxy,
    ds_device_proxy: DeviceProxy,
) -> None:
    # Put dish into maintenance mode
    mode_event_store = event_store_class()
    dsc_event_store = event_store_class()
    subscriptions = {}
    subscriptions.update(setup_subscriptions(dish_manager_proxy, {"dishMode": mode_event_store}))
    subscriptions.update(setup_subscriptions(ds_device_proxy, {"operatingMode": dsc_event_store}))
    dish_manager_proxy.SetMaintenanceMode()
    mode_event_store.wait_for_value(DishMode.MAINTENANCE, timeout=120)

    # unstow will be rejected unless the device has authority.
    # since ds device no longer waits for horn to go off when auth is
    # requested we need to take authority here and wait for the horn to go off
    ds_device_proxy.TakeAuthority()
    # wait 10s for the horn to go off
    mode_event_store.get_queue_values(timeout=10)
    ds_device_proxy.unstow()
    dsc_event_store.wait_for_value(DSOperatingMode.STANDBY, timeout=120)
    ds_device_proxy.slew([REQUESTED_AZIMUTH_VALUE, REQUESTED_ELEVATION_VALUE])
    dsc_event_store.wait_for_value(DSOperatingMode.POINT, timeout=30)
    assert dish_manager_proxy.dishMode == DishMode.MAINTENANCE

    mode_event_store.clear_queue()
    dish_manager_proxy.SetStowMode()
    mode_event_store.wait_for_value(DishMode.STOW, timeout=120)

    remove_subscriptions(subscriptions)
