import logging
import socket
from threading import Lock
from unittest import mock

import pytest
import tango
from ska_tango_base.control_model import CommunicationStatus
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
        tc_manager = TangoDeviceComponentManager(
            "fake/fqdn/1", LOGGER, Lock(), max_workers=1
        )
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


@pytest.mark.forked
@pytest.mark.unit
def test_happy_path(tango_test_context, caplog):
    caplog.set_level(logging.INFO)
    device_name = tango_test_context.name()
    _DeviceProxy = tango.DeviceProxy
    with mock.patch(
        "tango.DeviceProxy",
        wraps=lambda fqdn, *args, **kwargs: _DeviceProxy(
            "tango://{0}:{1}/{2}#dbase=no".format(get_host_ip(), PORT, fqdn),
            *args,
            **kwargs
        ),
    ):
        tc_manager = TangoDeviceComponentManager(
            device_name, LOGGER, Lock(), max_workers=1
        )
        tc_manager.start_communicating()
        while "Comms established" not in caplog.text:
            pass
        assert (
            tc_manager.communication_state == CommunicationStatus.ESTABLISHED
        )
