"""Testware for running ska-mid-dish-manager tests"""

import socket

import pytest
import tango
from tango import DevState
from tango.server import Device
from tango.test_context import (
    DeviceTestContext,
    MultiDeviceTestContext,
    get_host_ip,
)


# pylint: disable=invalid-name, missing-function-docstring
@pytest.fixture(scope="module", name="open_port")
def get_open_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="function")
def mock_tango_device_proxy_instance(mocker, open_port):
    HOST = get_host_ip()
    PORT = open_port
    _DeviceProxy = tango.DeviceProxy
    mocker.patch(
        "tango.DeviceProxy",
        wraps=lambda fqdn, *args, **kwargs: _DeviceProxy(
            f"tango://{HOST}:{PORT}/{fqdn}#dbase=no",
            *args,
            **kwargs,
        ),
    )
    return HOST, PORT


@pytest.fixture(name="SimpleDevice")
def simple_device():
    """
    Return the Tango event callback group under test.

    :return: the Tango event callback group under test.
    """

    # pylint: disable=missing-class-docstring, bad-super-call
    class SimpleDev(Device):
        def init_device(self):
            super(Device, self).init_device()
            self.set_state(DevState.ON)
            self.set_change_event("State", True)

    return SimpleDev


# pylint: disable=invalid-name, redefined-outer-name
@pytest.fixture
def simple_device_test_context(SimpleDevice, mock_tango_device_proxy_instance):
    """DeviceTestContext based off a custom tango device in SimpleDevice"""
    HOST, PORT = mock_tango_device_proxy_instance
    with DeviceTestContext(SimpleDevice, host=HOST, port=PORT) as proxy:
        yield proxy


@pytest.fixture(scope="module")
def devices_to_test(request):
    """Fixture for devices to test."""
    raise NotImplementedError(
        "You have to specify the devices totest by "
        " overriding the 'devices_to_test' fixture."
    )


# pylint: disable=invalid-name, redefined-outer-name
@pytest.fixture(scope="function")
def multi_device_tango_context(
    mock_tango_device_proxy_instance,
    devices_to_test,
):
    """
    Create and return a TANGO MultiDeviceTestContext object.

    tango.DeviceProxy patched to work around a name-resolving issue.
    """
    HOST, PORT = mock_tango_device_proxy_instance
    with MultiDeviceTestContext(
        devices_to_test, host=HOST, port=PORT, process=True
    ) as context:
        yield context
