"""Tango device component manager tests"""
import logging

import pytest
import tango
from ska_control_model import CommunicationStatus

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
        ("state", "polled_attr_1", "non_polled_attr_1"),
        component_state_callback=component_state_store,
    )

    assert com_man.sub_communication_state == CommunicationStatus.NOT_ESTABLISHED

    com_man.start_communicating()
    assert com_man.sub_communication_state == CommunicationStatus.ESTABLISHED
    com_man.execute_command("On", None)
    assert component_state_store.wait_for_value("state", tango.DevState.ON, timeout=5)

    com_man.execute_command("IncrementNonPolled1", None)
    assert component_state_store.wait_for_value(
        "non_polled_attr_1", device_proxy.non_polled_attr_1
    )

    com_man.stop_communicating()
    assert com_man.sub_communication_state == CommunicationStatus.NOT_ESTABLISHED


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_stress_component_monitor(component_state_store, ds_device_fqdn):
    """Stress test component updates"""
    device_proxy = tango.DeviceProxy(ds_device_fqdn)
    com_man = TangoDeviceComponentManager(
        ds_device_fqdn,
        LOGGER,
        ("non_polled_attr_1"),
        component_state_callback=component_state_store,
    )
    com_man.start_communicating()
    for _ in range(10):
        com_man.execute_command("IncrementNonPolled1", None)
        assert component_state_store.wait_for_value(
            "non_polled_attr_1", device_proxy.non_polled_attr_1
        )
