# pylint: disable=abstract-method
# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
import logging
import socket
from unittest import mock

import pytest
import tango
from ska_tango_base.control_model import CommunicationStatus
from ska_tango_testing.mock import MockCallableGroup
from tango.test_context import DeviceTestContext, get_host_ip

from ska_mid_dish_manager.component_managers.tango_device_cm import (
    TangoDeviceComponentManager,
)

LOGGER = logging.getLogger(__name__)


def _get_open_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


PORT = _get_open_port()


@pytest.mark.timeout(10)
@pytest.mark.forked
@pytest.mark.unit
def test_non_existing_component(caplog):
    caplog.set_level(logging.INFO)
    _DeviceProxy = tango.DeviceProxy
    with mock.patch(
        "tango.DeviceProxy",
        wraps=lambda fqdn, *args, **kwargs: _DeviceProxy(
            "tango://{0}:{1}/{2}#dbase=no".format(get_host_ip(), PORT, fqdn),
            *args,
            **kwargs
        ),
    ):
        tc_manager = TangoDeviceComponentManager("fake/fqdn/1", LOGGER)
        tc_manager.start_communicating()
        while "Connection retry count [3]" not in caplog.text:
            pass
        assert (
            tc_manager.communication_state
            == CommunicationStatus.NOT_ESTABLISHED
        )
        tc_manager.stop_communicating()


@pytest.fixture
def tango_test_context(SimpleDevice):
    _DeviceProxy = tango.DeviceProxy
    mock.patch(
        "tango.DeviceProxy",
        wraps=lambda fqdn, *args, **kwargs: _DeviceProxy(
            "tango://{0}:{1}/{2}#dbase=no".format(get_host_ip(), PORT, fqdn),
            *args,
            **kwargs
        ),
    )

    with DeviceTestContext(
        SimpleDevice, port=PORT, host=get_host_ip()
    ) as proxy:
        yield proxy


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.tango_device_cm.tango")
def test_happy_path(patched_tango, caplog):
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
    comm_call_group.assert_call(
        "comm_state", CommunicationStatus.NOT_ESTABLISHED
    )
    comm_call_group.assert_call(
        "comp_state", connection_state="setting_up_device_proxy"
    )
    comm_call_group.assert_call("comp_state", connection_state="connected")
    comm_call_group.assert_call(
        "comp_state", connection_state="setting_up_monitoring"
    )

    comm_call_group.assert_call("comp_state", connection_state="monitoring")
    comm_call_group.assert_call("comm_state", CommunicationStatus.ESTABLISHED)

    tc_manager.abort_tasks()


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.tango_device_cm.tango")
def test_unhappy_path(patched_tango, caplog):
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

    with mock.patch.object(
        tc_manager, "_log_message", log_call_group["log_message"]
    ):
        assert tc_manager.state == "disconnected"
        tc_manager.start_communicating()

        log_call_group.assert_call(
            "log_message",
            "Connection retry count [3] for device [a/b/c]",
            lookahead=10,
        )

        assert tc_manager.state == "setting_up_device_proxy"

        tc_manager.abort_tasks()
