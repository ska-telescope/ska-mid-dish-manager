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
# @pytest.mark.timeout(10)
# @pytest.mark.forked
@pytest.mark.unit
def test_component_manager_continues_reconnecting_when_device_is_unreachable(caplog):
    caplog.set_level(logging.DEBUG)
    tc_manager = TangoDeviceComponentManager("fake/fqdn/1", LOGGER, ("fake_attr",))
    tc_manager.start_communicating()
    while "An error occured creating a device proxy to fake/fqdn/1" not in caplog.text:
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
@mock.patch("ska_mid_dish_manager.component_managers.device_monitor.DeviceProxyManager")
def test_unhappy_path(patched_dev_factory, caplog):
    """Tango device is unreachable and can't communicate with component manager

    Similar to `test_component_manager_continues_reconnecting_...` except
    Tango layer is mocked here. Checks are made on the mock for expected
    calls and logs when communication is attempted by component manager
    on mocked device
    """
    # pylint: disable=no-member
    caplog.set_level(logging.DEBUG)

    # Set up mocks
    mock_device_proxy = mock.MagicMock(name="DP")
    mock_device_proxy.ping.side_effect = tango.DevFailed("FAIL")

    class DummyFactory:
        def __call__(self, *args, **kwargs):
            return mock_device_proxy

    patched_dev_factory.return_value = DummyFactory()

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
        tc_manager._events_queue.get(timeout=6)
    except Empty:
        pass
    logs = [record.message for record in caplog.records]
    for count in ("0", "1", "2"):
        # assert f"Tango error on a/b/c for attr {the_attr}, try number {count}" in logs
        assert f"Cannot connect to a/b/c try number {count}" in logs


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.device_monitor.DeviceProxyManager")
def test_device_goes_away(patched_dev_factory, caplog):
    """Start up the component_manager.
    Signal a lost connection via an event
    Check for reconnect
    """
    caplog.set_level(logging.DEBUG)

    # Set up mocks
    mock_device_proxy = mock.MagicMock()
    mock_device_proxy.command_inout = mock.MagicMock()
    mock_device_proxy.ping = mock.MagicMock()

    class DummyFactory:
        def __call__(self, *args, **kwargs):
            return mock_device_proxy

    patched_dev_factory.return_value = DummyFactory()

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
