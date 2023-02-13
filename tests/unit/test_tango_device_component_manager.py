# pylint: disable=protected-access
"""Unit tests checking generic component manager behaviour."""

import logging
from queue import Empty
from unittest import mock

import pytest
import tango
from ska_control_model import CommunicationStatus

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
    tc_manager = TangoDeviceComponentManager("fake/fqdn/1", LOGGER, ("fake_attr",))
    tc_manager.start_communicating()
    while "Connection retry count [3]" not in caplog.text:
        pass
    assert tc_manager.communication_state == CommunicationStatus.NOT_ESTABLISHED
    tc_manager.stop_communicating()


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.device_monitor.tango")
def test_happy_path(patched_tango, caplog):
    """Tango device is reachable and communicates with component manager

    Tango layer is mocked and checks are made on the mock for expected
    calls made when communication is established and component is
    updated accordingly
    """
    # pylint: disable=no-member
    caplog.set_level(logging.DEBUG)

    patched_dp = mock.MagicMock()
    patched_dp.command_inout = mock.MagicMock()
    patched_tango.DeviceProxy = mock.MagicMock(return_value=patched_dp)

    comm_state_cb = mock.MagicMock()
    comp_state_cb = mock.MagicMock()

    tc_manager = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        ("some_attr",),
        communication_state_callback=comm_state_cb,
        component_state_callback=comp_state_cb,
    )

    tc_manager.start_communicating()
    assert comm_state_cb.called


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.device_monitor.tango")
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

    # Set up mocks
    mock_device_proxy = mock.MagicMock(name="DP")
    mock_device_proxy.ping.side_effect = tango.DevFailed("FAIL")
    patched_tango.DeviceProxy.return_value = mock_device_proxy

    tc_manager = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        ("some_attr", "some_other_attr"),
        communication_state_callback=None,
        component_state_callback=None,
    )

    tc_manager.start_communicating()
    # Wait a bit
    try:
        tc_manager._events_queue.get(timeout=3)
    except Empty:
        pass
    logs = [record.message for record in caplog.records]
    for count, the_attr in zip(["1", "2", "3"], ["some_attr", "some_other_attr"]):
        assert f"Error on Tango a/b/c for attr {the_attr}, try number {count}" in logs


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.device_monitor.tango")
def test_device_goes_away(patched_tango, caplog):
    """Start up the component_manager.
    Signal a lost connection via an event
    Check for reconnect
    """
    caplog.set_level(logging.DEBUG)

    # Set up mocks
    patched_dp = mock.MagicMock()
    patched_dp.command_inout = mock.MagicMock()
    patched_dp.ping = mock.MagicMock()
    patched_tango.DeviceProxy = mock.MagicMock(return_value=patched_dp)
    patched_tango.DevFailed = tango.DevFailed

    tc_manager = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        ("some_,attr",),
    )

    tc_manager.start_communicating()

    # Set up mock error event
    mock_error = mock.MagicMock()
    mock_error.err = True

    # Trigger the failure
    tc_manager._events_queue.put(mock_error)

    tc_manager.abort_commands()
