"""Contains pytest fixtures for other tests setup"""

import queue
import socket
from typing import Any

import pytest
import tango
from tango import DevState
from tango.server import Device
from tango.test_context import DeviceTestContext, MultiDeviceTestContext, get_host_ip

from tests.utils import EventStore


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

    # pylint: disable=bad-super-call, too-few-public-methods
    class SimpleDev(Device):
        """A basic device which pushes change events on State"""

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


@pytest.fixture(scope="module")  # noqa: F811
def devices_to_test(request):
    yield getattr(request.module, "devices_to_test")


# pylint: disable=invalid-name, redefined-outer-name
@pytest.fixture(scope="function")
def multi_device_tango_context(mocker, devices_to_test):  # pylint: disable=redefined-outer-name
    """
    Creates and returns a TANGO MultiDeviceTestContext object, with
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
            f"tango://{HOST}:{PORT}/{fqdn}#dbase=no",
            *args,
            **kwargs,
        ),
    )
    with MultiDeviceTestContext(devices_to_test, host=HOST, port=PORT, process=True) as context:
        yield context


@pytest.fixture(scope="function")
def event_store():  # pylint: disable=too-many-statements
    """Fixture for storing events"""
    return EventStore()


@pytest.fixture(scope="function")
def event_store_class():  # pylint: disable=too-many-statements
    """Fixture for storing events"""
    return EventStore


@pytest.fixture(scope="function")
def component_state_store():
    """Fixture for storing component state changes over time"""

    class ComponentStateStore:
        """Store component state changes with useful functionality"""

        def __init__(self) -> None:
            self._queue = queue.Queue()

        def __call__(self, *args, **kwargs):
            """Store the update component_state

            :param event: latest_state
            :type event: dict
            """
            self._queue.put(kwargs)

        def wait_for_value(  # pylint:disable=inconsistent-return-statements
            self, key: str, value: Any, timeout: int = 3
        ):
            """Wait for a value to arrive

            Wait `timeout` seconds for each fetch.

            :param key: The value key
            :type value: str
            :param value: The value to check for
            :type value: Any
            :param timeout: the get timeout, defaults to 3
            :type timeout: int, optional
            :raises RuntimeError: If None are found
            :return: True if found
            :rtype: bool
            """
            try:
                found_events = []
                while True:
                    state = self._queue.get(timeout=timeout)
                    if key in state:
                        if state[key] == value:
                            return True
                    found_events.append(state)
            except queue.Empty as err:
                raise RuntimeError(
                    (
                        f"Never got a state with key [{key}], value "
                        f"[{value}], got [{found_events}]"
                    )
                ) from err

        def clear_queue(self):
            while not self._queue.empty():
                self._queue.get()

    return ComponentStateStore()


@pytest.fixture
def dish_manager_device_fqdn():
    return "ska001/elt/master"


@pytest.fixture
def ds_device_fqdn():
    return "ska001/lmc/ds_simulator"


@pytest.fixture
def spf_device_fqdn():
    return "ska001/spf/simulator"


@pytest.fixture
def spfrx_device_fqdn():
    return "ska001/spfrx/simulator"


@pytest.fixture
def dish_manager_proxy(dish_manager_device_fqdn):
    return tango.DeviceProxy(dish_manager_device_fqdn)


@pytest.fixture
def ds_device_proxy(ds_device_fqdn):
    return tango.DeviceProxy(ds_device_fqdn)


@pytest.fixture
def spf_device_proxy(spf_device_fqdn):
    return tango.DeviceProxy(spf_device_fqdn)


@pytest.fixture
def spfrx_device_proxy(spfrx_device_fqdn):
    return tango.DeviceProxy(spfrx_device_fqdn)
