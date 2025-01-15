"Test log of command and attribute write failures"
# pylint: disable=no-member,protected-access
import logging

import mock
import pytest
import tango
from ska_control_model import CommunicationStatus

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager

LOGGER = logging.getLogger(__name__)


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.tango_device_cm.DeviceProxyManager")
def test_log_command_inout(patched_dev_factory, caplog: pytest.LogCaptureFixture):
    """Check that exceptions for command_inout is logged"""
    caplog.set_level(logging.DEBUG)

    # Set up mocks
    mock_device_proxy = mock.MagicMock(name="DP")
    mock_device_proxy.command_inout.side_effect = tango.DevFailed("Failure Message")

    class DummyFactory:
        def __call__(self, *args, **kwargs):
            return mock_device_proxy

    patched_dev_factory.return_value = DummyFactory()

    tc_manager = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        (),
    )

    tc_manager._update_communication_state(communication_state=CommunicationStatus.ESTABLISHED)
    with pytest.raises(tango.DevFailed):
        tc_manager.execute_command("Stow", None)

    assert "Traceback" in caplog.text
    assert "Failure Message" in caplog.text
    assert "Could not execute command [Stow] with arg [None] on [a/b/c]" in caplog.text

    # Check that at least one exception is logged
    assert any(i.exc_info for i in caplog.records)


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.tango_device_cm.DeviceProxyManager")
def test_log_write_attribute(patched_dev_factory, caplog: pytest.LogCaptureFixture):
    """Check that exceptions for write_attribute_value is logged"""
    caplog.set_level(logging.DEBUG)

    # Set up mocks
    mock_device_proxy = mock.MagicMock(name="DP")
    mock_device_proxy.write_attribute.side_effect = tango.DevFailed("Failure Message")

    class DummyFactory:
        def __call__(self, *args, **kwargs):
            return mock_device_proxy

    patched_dev_factory.return_value = DummyFactory()

    tc_manager = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        (),
    )

    tc_manager._update_communication_state(communication_state=CommunicationStatus.ESTABLISHED)
    with pytest.raises(tango.DevFailed):
        tc_manager.write_attribute_value("attr", "val")

    assert "Traceback" in caplog.text
    assert "Failure Message" in caplog.text
    assert "Could not write to attribute [attr] with [val] on [a/b/c]" in caplog.text

    # Check that at least one exception is logged
    assert any(i.exc_info for i in caplog.records)
