import logging

import mock
import pytest
import tango
from ska_control_model import CommunicationStatus

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager

LOGGER = logging.getLogger(__name__)


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.tango_device_cm.tango")
def test_log_command_inout(patched_tango, caplog):
    """Check that exceptions for command_inout is logged"""
    # pylint: disable=no-member
    patched_tango.DevFailed = tango.DevFailed
    caplog.set_level(logging.DEBUG)

    # Set up mocks
    mock_device_proxy = mock.MagicMock(name="DP")
    mock_device_proxy.command_inout.side_effect = tango.DevFailed("Failure Message")
    patched_tango.DeviceProxy.return_value = mock_device_proxy

    tc_manager = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        [],
        communication_state_callback=None,
        component_state_callback=None,
    )

    tc_manager._update_communication_state(communication_state=CommunicationStatus.ESTABLISHED)
    with pytest.raises(tango.DevFailed):
        tc_manager.execute_command("Stow", None)

    assert "Traceback" in caplog.text
    assert "Failure Message" in caplog.text

    # Check that at least one exception is logged
    assert any([i.exc_info for i in caplog.records])


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.tango_device_cm.tango")
def test_log_write_attribute(patched_tango, caplog):
    """Check that exceptions for write_attribute_value is logged"""
    # pylint: disable=no-member
    patched_tango.DevFailed = tango.DevFailed
    caplog.set_level(logging.DEBUG)

    # Set up mocks
    mock_device_proxy = mock.MagicMock(name="DP")
    mock_device_proxy.write_attribute.side_effect = tango.DevFailed("Failure Message")
    patched_tango.DeviceProxy.return_value = mock_device_proxy

    tc_manager = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        [],
        communication_state_callback=None,
        component_state_callback=None,
    )

    tc_manager._update_communication_state(communication_state=CommunicationStatus.ESTABLISHED)
    with pytest.raises(tango.DevFailed):
        tc_manager.write_attribute_value("attr", "val")

    assert "Traceback" in caplog.text
    assert "Failure Message" in caplog.text

    # Check that at least one exception is logged
    assert any([i.exc_info for i in caplog.records])
