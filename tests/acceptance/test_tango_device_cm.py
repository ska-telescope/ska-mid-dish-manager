"""Tango device component manager tests"""
import logging

import pytest
import tango

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager

LOGGER = logging.getLogger(__name__)


# pylint:disable=protected-access
@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_tango_device_component_manager_state(component_state_store, ds_device_fqdn):
    """Test commands and monitoring"""
    device_proxy = tango.DeviceProxy(ds_device_fqdn)
    assert device_proxy.ping()

    com_man = TangoDeviceComponentManager(
        ds_device_fqdn,
        LOGGER,
        component_state_callback=component_state_store,
    )

    assert com_man.component_state["connection_state"] == "disconnected"

    com_man.start_communicating()
    assert component_state_store.wait_for_value("connection_state", "setting_up_monitoring")
    assert component_state_store.wait_for_value("connection_state", "monitoring")

    com_man.execute_command(device_proxy, "On", None)
    assert component_state_store.wait_for_value("state", tango.DevState.ON, timeout=5)

    com_man.monitor_attribute("polled_attr_1")
    assert component_state_store.wait_for_value("polled_attr_1", device_proxy.polled_attr_1)

    com_man.monitor_attribute("non_polled_attr_1")
    com_man.execute_command(device_proxy, "IncrementNonPolled1", None)
    assert component_state_store.wait_for_value(
        "non_polled_attr_1", device_proxy.non_polled_attr_1
    )

    com_man.stop_communicating()
    assert component_state_store.wait_for_value("connection_state", "disconnected")


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_stress_connect_disconnect(component_state_store, ds_device_fqdn):
    """Test connect and disconnect"""
    device_proxy = tango.DeviceProxy(ds_device_fqdn)
    assert device_proxy.ping()

    com_man = TangoDeviceComponentManager(
        ds_device_fqdn,
        LOGGER,
        component_state_callback=component_state_store,
    )
    assert com_man.component_state["connection_state"] == "disconnected"
    for i in range(10):
        com_man.start_communicating()
        assert component_state_store.wait_for_value("connection_state", "setting_up_device_proxy")
        assert component_state_store.wait_for_value("connection_state", "setting_up_monitoring")
        assert component_state_store.wait_for_value("connection_state", "monitoring")
        # This is only updated once, from that point it doesn't change
        if i == 0:
            assert component_state_store.wait_for_value("state", tango.DevState.ON)
        com_man.stop_communicating()
        assert component_state_store.wait_for_value("connection_state", "disconnected")


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_stress_component_monitor(component_state_store, ds_device_fqdn):
    """Stress test component updates"""
    device_proxy = tango.DeviceProxy(ds_device_fqdn)
    com_man = TangoDeviceComponentManager(
        ds_device_fqdn,
        LOGGER,
        component_state_callback=component_state_store,
    )
    com_man.start_communicating()
    assert component_state_store.wait_for_value("connection_state", "monitoring")
    com_man.monitor_attribute("non_polled_attr_1")
    for _ in range(10):
        com_man.execute_command(device_proxy, "IncrementNonPolled1", None)
        assert component_state_store.wait_for_value(
            "non_polled_attr_1", device_proxy.non_polled_attr_1
        )
