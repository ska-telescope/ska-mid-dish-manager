"""Tango device component manager tests"""
import logging

import pytest
import tango
from ska_control_model import CommunicationStatus
from ska_tango_testing.mock import MockCallable

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager

LOGGER = logging.getLogger(__name__)


# pylint:disable=protected-access,unused-argument
@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_tango_device_component_manager_state(
    monitor_tango_servers, component_state_store, ds_device_fqdn
):
    """Test commands and monitoring"""
    mock_callable = MockCallable(timeout=5)

    device_proxy = tango.DeviceProxy(ds_device_fqdn)
    assert device_proxy.ping()

    com_man = TangoDeviceComponentManager(
        ds_device_fqdn,
        LOGGER,
        ("operatingMode", "healthState"),
        component_state_callback=component_state_store,
        communication_state_callback=mock_callable,
    )
    assert com_man.communication_state == CommunicationStatus.NOT_ESTABLISHED

    com_man.start_communicating()

    mock_callable.assert_call(CommunicationStatus.ESTABLISHED, lookahead=3)

    assert com_man.communication_state == CommunicationStatus.ESTABLISHED

    com_man.stop_communicating()
    assert com_man.communication_state == CommunicationStatus.NOT_ESTABLISHED


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_stress_component_monitor(component_state_store, ds_device_fqdn):
    """Stress test component updates"""
    mock_callable = MockCallable(timeout=5)

    com_man = TangoDeviceComponentManager(
        ds_device_fqdn,
        LOGGER,
        ("operatingMode",),
        component_state_callback=component_state_store,
        communication_state_callback=mock_callable,
    )

    com_man.start_communicating()

    mock_callable.assert_call(CommunicationStatus.ESTABLISHED, lookahead=3)
