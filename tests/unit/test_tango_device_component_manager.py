# pylint: disable=protected-access
"""Unit tests checking generic component manager behaviour."""

import logging
from unittest import mock

import pytest
import tango
from ska_tango_base.control_model import CommunicationStatus
from ska_tango_testing.mock import MockCallableGroup

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager

LOGGER = logging.getLogger(__name__)


# pylint: disable=invalid-name, missing-function-docstring
@pytest.mark.timeout(10)
@pytest.mark.forked
@pytest.mark.unit
def test_component_manager_continues_reconnecting_when_device_is_unreachable(
    caplog, mock_tango_device_proxy_instance
):
    caplog.set_level(logging.DEBUG)
    _, _ = mock_tango_device_proxy_instance
    tc_manager = TangoDeviceComponentManager("fake/fqdn/1", LOGGER)
    tc_manager.start_communicating()
    while "Connection retry count [3]" not in caplog.text:
        pass
    assert tc_manager.communication_state == CommunicationStatus.NOT_ESTABLISHED
    tc_manager.stop_communicating()


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.tango_device_cm.tango")
def test_happy_path(patched_tango, caplog):
    """Tango device is reachable and communicates with component manager

    Tango layer is mocked and checks are made on the mock for expected
    calls made when communication is established and component is
    updated accordingly
    """
    # pylint: disable=no-member
    caplog.set_level(logging.DEBUG)

    comm_call_group = MockCallableGroup("comm_state", "comp_state", timeout=3)

    # Set up mocks
    patched_dp = mock.MagicMock()
    patched_dp.command_inout = mock.MagicMock()
    patched_tango.DeviceProxy = mock.MagicMock(return_value=patched_dp)

    tc_manager = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        communication_state_callback=comm_call_group["comm_state"],
        component_state_callback=comm_call_group["comp_state"],
    )

    assert tc_manager.state == "disconnected"

    tc_manager.start_communicating()
    comm_call_group.assert_call("comm_state", CommunicationStatus.NOT_ESTABLISHED)
    comm_call_group.assert_call("comp_state", connection_state="setting_up_device_proxy")
    comm_call_group.assert_call("comp_state", connection_state="setting_up_monitoring")

    comm_call_group.assert_call("comp_state", connection_state="monitoring")
    comm_call_group.assert_call("comm_state", CommunicationStatus.ESTABLISHED)

    tc_manager.abort_commands()


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.tango_device_cm.tango")
def test_unhappy_path(patched_tango, caplog):
    """Tango device is unreachable and can't communicate with component manager

    Similar to `test_component_manager_continues_reconnecting_...` except
    Tango layer is mocked here. Checks are made on the mock for expected
    calls and logs when communication is attempted by component manager
    on mocked device
    """
    # pylint: disable=no-member
    patched_tango.DevFailed = tango.DevFailed
    caplog.set_level(logging.DEBUG)

    log_call_group = MockCallableGroup("log_message", timeout=5)

    # Set up mocks
    mock_device_proxy = mock.MagicMock(name="DP")
    mock_device_proxy.ping.side_effect = tango.DevFailed("FAIL")
    patched_tango.DeviceProxy.return_value = mock_device_proxy

    tc_manager = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        communication_state_callback=None,
        component_state_callback=None,
    )

    with mock.patch.object(tc_manager.logger, "info", log_call_group["log_message"]):
        assert tc_manager.state == "disconnected"  # pylint: disable=no-member
        tc_manager.start_communicating()

        log_call_group.assert_call(
            "log_message",
            "Connection retry count [%s] for device [%s]",
            4,
            "a/b/c",
            lookahead=10,
        )

        assert tc_manager.state == "setting_up_device_proxy"

        tc_manager.abort_commands()


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.tango_device_cm.tango")
def test_device_goes_away(patched_tango, caplog):
    """Start up the component_manager.
    Signal a lost connection via an event
    Check for reconnect
    """
    caplog.set_level(logging.DEBUG)

    call_group = MockCallableGroup("comm_state", "comp_state", timeout=5)

    # Set up mocks
    patched_dp = mock.MagicMock()
    patched_dp.command_inout = mock.MagicMock()
    patched_tango.DeviceProxy = mock.MagicMock(return_value=patched_dp)

    tc_manager = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        communication_state_callback=call_group["comm_state"],
        component_state_callback=call_group["comp_state"],
    )

    assert tc_manager.state == "disconnected"  # pylint:disable=no-member

    tc_manager.start_communicating()
    call_group.assert_call("comm_state", CommunicationStatus.NOT_ESTABLISHED)
    call_group.assert_call("comp_state", connection_state="setting_up_device_proxy")
    call_group.assert_call("comp_state", connection_state="setting_up_monitoring")
    call_group.assert_call("comp_state", connection_state="monitoring")
    call_group.assert_call("comm_state", CommunicationStatus.ESTABLISHED)

    # Set up mock error event
    mock_error = mock.MagicMock()
    mock_error.err = True

    # Trigger the failure
    tc_manager._events_queue.put(mock_error)

    # Make sure we lost connection
    call_group.assert_call("comm_state", CommunicationStatus.NOT_ESTABLISHED)
    # Make sure we get it back
    call_group.assert_call("comp_state", connection_state="reconnecting")
    call_group.assert_call("comp_state", connection_state="setting_up_device_proxy")
    call_group.assert_call("comp_state", connection_state="setting_up_monitoring")
    call_group.assert_call("comp_state", connection_state="monitoring")
    call_group.assert_call("comm_state", CommunicationStatus.ESTABLISHED)
    tc_manager.abort_commands()
