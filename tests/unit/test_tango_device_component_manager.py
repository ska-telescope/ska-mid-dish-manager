"""Unit tests checking generic component manager behaviour."""

import logging
from threading import Lock

import pytest
from ska_tango_base.control_model import CommunicationStatus

from ska_mid_dish_manager.component_managers.tango_device_cm import (
    TangoDeviceComponentManager,
)

LOGGER = logging.getLogger(__name__)


# pylint: disable=invalid-name, missing-function-docstring
@pytest.mark.timeout(10)
@pytest.mark.forked
@pytest.mark.unit
def test_non_existing_component(caplog, mock_tango_device_proxy_instance):
    caplog.set_level(logging.INFO)
    _, _ = mock_tango_device_proxy_instance
    tc_manager = TangoDeviceComponentManager(
        "fake/fqdn/1", LOGGER, Lock(), max_workers=1
    )
    tc_manager.start_communicating()
    while "Connection retry count [3]" not in caplog.text:
        pass
    assert (
        tc_manager.communication_state == CommunicationStatus.NOT_ESTABLISHED
    )
    tc_manager.stop_communicating()


# pylint: disable=invalid-name, missing-function-docstring
@pytest.mark.forked
@pytest.mark.unit
def test_happy_path(
    simple_device_test_context, mock_tango_device_proxy_instance, caplog
):
    caplog.set_level(logging.INFO)
    device_name = simple_device_test_context.name()
    _, _ = mock_tango_device_proxy_instance
    tc_manager = TangoDeviceComponentManager(
        device_name, LOGGER, Lock(), max_workers=1
    )
    tc_manager.start_communicating()
    while "Comms established" not in caplog.text:
        pass
    assert tc_manager.communication_state == CommunicationStatus.ESTABLISHED
