"""Tests for running ska-mid-dish-manager tests"""

import queue
import socket
from typing import Any

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

    # pylint: disable=bad-super-call, too-few-public-methods
    class SimpleDev(Device):
        """Simple device"""

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
def multi_device_tango_context(
    mocker, devices_to_test  # pylint: disable=redefined-outer-name
):
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
    with MultiDeviceTestContext(
        devices_to_test, host=HOST, port=PORT, process=True
    ) as context:
        yield context


@pytest.fixture(scope="function")
def event_store():
    """Fixture for storing events"""

    class EventStore:
        """Store events with useful functionality"""

        def __init__(self) -> None:
            self._queue = queue.Queue()

        def push_event(self, event: tango.EventData):
            """Store the event

            :param event: Tango event
            :type event: tango.EventData
            """
            self._queue.put(event)

        def wait_for_value(  # pylint:disable=inconsistent-return-statements
            self, value: Any, timeout: int = 3
        ):
            """Wait for a value to arrive

            Wait `timeout` seconds for each fetch.

            :param value: The value to check for
            :type value: Any
            :param timeout: the get timeout, defaults to 3
            :type timeout: int, optional
            :raises RuntimeError: If None are found
            :return: True if found
            :rtype: bool
            """
            try:
                while True:
                    event = self._queue.get(timeout=timeout)
                    if not event.attr_value:
                        continue
                    if event.attr_value.value != value:
                        continue
                    if event.attr_value.value == value:
                        return True
            except queue.Empty as err:
                raise RuntimeError(
                    f"Never got an event with value [{value}]"
                ) from err

        # pylint:disable=inconsistent-return-statements
        def wait_for_command_result(
            self, command_id: str, command_result: Any, timeout: int = 5
        ):
            """Wait for a long running command result

            Wait `timeout` seconds for each fetch.

            :param command_id: The long running command ID
            :type command_id: str
            :param timeout: the get timeout, defaults to 3
            :type timeout: int, optional
            :raises RuntimeError: If none are found
            :return: The result of the long running command
            :rtype: str
            """
            try:
                while True:
                    event = self._queue.get(timeout=timeout)
                    if not event.attr_value:
                        continue
                    if not isinstance(event.attr_value.value, tuple):
                        continue
                    if len(event.attr_value.value) != 2:
                        continue
                    (lrc_id, lrc_result) = event.attr_value.value
                    if command_id == lrc_id and command_result == lrc_result:
                        return True
            except queue.Empty as err:
                raise RuntimeError(
                    f"Never got an LRC result from command [{command_id}]"
                ) from err

        def wait_for_command_id(self, command_id: str, timeout: int = 5):
            """Wait for a long running command to complete

            Wait `timeout` seconds for each fetch.

            :param command_id: The long running command ID
            :type command_id: str
            :param timeout: the get timeout, defaults to 3
            :type timeout: int, optional
            :raises RuntimeError: If none are found
            :return: The result of the long running command
            :rtype: str
            """
            try:
                while True:
                    event = self._queue.get(timeout=timeout)
                    if not event.attr_value:
                        continue
                    if not isinstance(event.attr_value.value, tuple):
                        continue
                    if len(event.attr_value.value) != 2:
                        continue
                    (lrc_id, _) = event.attr_value.value
                    if command_id == lrc_id:
                        return True
            except queue.Empty as err:
                raise RuntimeError(
                    f"Never got an LRC result from command [{command_id}]"
                ) from err

        def clear_queue(self):
            while not self._queue.empty():
                self._queue.get()

        #  pylint: disable=unused-argument
        def get_queue_events(self, timeout: int = 3):
            items = []
            try:
                while True:
                    items.append(self._queue.get(timeout=timeout))
            except queue.Empty:
                return items

        def get_queue_values(self, timeout: int = 3):
            items = []
            try:
                while True:
                    event = self._queue.get(timeout=timeout)
                    items.append(
                        (event.attr_value.name, event.attr_value.value)
                    )
            except queue.Empty:
                return items

    return EventStore()


@pytest.fixture(scope="function")
def component_state_store():
    """Fixture for storing component state changes over time"""

    class ComponentStateStore:
        """Store componen state changes with useful functionality"""

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
                while True:
                    state = self._queue.get(timeout=timeout)
                    if key in state:
                        if state[key] == value:
                            return True
                    continue
            except queue.Empty as err:
                raise RuntimeError(
                    f"Never got a state with key [{key}], value [{value}]"
                ) from err

        def clear_queue(self):
            while not self._queue.empty():
                self._queue.get()

    return ComponentStateStore()


@pytest.fixture
def ds_device_fqdn():
    return "mid_d0001/lmc/ds_simulator"