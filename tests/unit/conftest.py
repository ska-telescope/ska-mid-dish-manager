import socket

import pytest
import tango
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango import DevState
from tango.server import Device
from tango.test_context import MultiDeviceTestContext, get_host_ip


class SimpleDev(Device):
    def init_device(self):
        super(Device, self).init_device()
        self.set_state(DevState.ON)
        self.set_change_event("State", True)


@pytest.fixture(name="SimpleDevice")
def simple_device():
    """
    Return the Tango event callback group under test.

    :return: the Tango event callback group under test.
    """
    return SimpleDev


@pytest.fixture()
def change_event_cb() -> MockTangoEventCallbackGroup:
    """
    Return the Tango event callback group under test.

    :return: the Tango event callback group under test.
    """
    return MockTangoEventCallbackGroup(
        "dishMode",
        timeout=2.0,
    )


@pytest.fixture(scope="module")
def devices_to_test(request):
    """Fixture for devices to test."""
    raise NotImplementedError(
        "You have to specify the devices totest by "
        " overriding the 'devices_to_test' fixture."
    )


@pytest.fixture(scope="function")
def multi_device_tango_context(
    mocker, devices_to_test  # pylint: disable=redefined-outer-name
):
    """
    Create and return a TANGO MultiDeviceTestContext object.

    tango.DeviceProxy patched to work around a name-resolving issue.
    """

    def _get_open_port():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
        s.close()
        return port

    HOST = get_host_ip()
    PORT = _get_open_port()
    _DeviceProxy = tango.DeviceProxy
    mocker.patch(
        "tango.DeviceProxy",
        wraps=lambda fqdn, *args, **kwargs: _DeviceProxy(
            "tango://{0}:{1}/{2}#dbase=no".format(HOST, PORT, fqdn),
            *args,
            **kwargs
        ),
    )
    with MultiDeviceTestContext(
        devices_to_test, host=HOST, port=PORT, process=True
    ) as context:
        yield context
