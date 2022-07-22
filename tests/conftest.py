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
        "You have to specify the devices to test by "
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

        def clear_queue(self):
            while not self._queue.empty():
                self._queue.get()

    return EventStore()


@pytest.fixture(scope="function")
def component_state_store():
    """Fixture for storing events"""

    class ComponentStateStore:
        """Store events with useful functionality"""

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
