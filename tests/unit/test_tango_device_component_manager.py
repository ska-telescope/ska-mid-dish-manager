import logging
import socket
from unittest import mock

import pytest
from ska_tango_base.control_model import CommunicationStatus

from ska_mid_dish_manager.component_managers import TangoDeviceComponentManager

import tango
from tango import DevState
from tango.server import Device
from tango.test_context import get_host_ip, DeviceTestContext

LOGGER = logging.getLogger(__name__)


@pytest.mark.timeout(10)
def test_non_existing_component(caplog):
    caplog.set_level(logging.INFO)
    tc_manager = TangoDeviceComponentManager(
        "fake/fqdn/1", max_workers=1, logger=LOGGER
    )
    while "Connection retry count [3]" not in caplog.text:
        pass
    assert tc_manager.communication_state == CommunicationStatus.DISABLED
    tc_manager.stop_communicating()
    assert (
        tc_manager.communication_state == CommunicationStatus.NOT_ESTABLISHED
    )

class TestDevice(Device):
    def init_device(self):
        super(Device, self).init_device()
        self.set_state(DevState.ON)
        self.set_change_event("State", True, True)


def _get_open_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port

PORT = _get_open_port()


@pytest.fixture
def tango_test_context():
    _DeviceProxy = tango.DeviceProxy
    mock.patch(
        'tango.DeviceProxy',
        wraps=lambda fqdn, *args, **kwargs: _DeviceProxy(
            "tango://{0}:{1}/{2}#dbase=no".format(get_host_ip(), PORT, fqdn),
            *args,
            **kwargs
        )
    )

    with DeviceTestContext(TestDevice, port=PORT, host=get_host_ip()) as proxy:
        yield proxy


@pytest.mark.forked
def test_happy_path(tango_test_context):
    device_name = tango_test_context.name()
    _DeviceProxy = tango.DeviceProxy
    with mock.patch(
        'tango.DeviceProxy',
        wraps=lambda fqdn, *args, **kwargs: _DeviceProxy(
            "tango://{0}:{1}/{2}#dbase=no".format(get_host_ip(), PORT, fqdn),
            *args,
            **kwargs
        )
    ):
        tc_manager = TangoDeviceComponentManager(
            device_name, max_workers=1, logger=LOGGER
        )
        tc_manager.communication_state == CommunicationStatus.ESTABLISHED
