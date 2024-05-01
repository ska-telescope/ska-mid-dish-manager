"""Contains pytest fixtures for other tests setup"""
# pylint: disable=too-many-statements,invalid-name,missing-function-docstring,redefined-outer-name

import os
import queue
import socket
from dataclasses import dataclass, field
from typing import Any, List, Tuple

import pytest
import tango
from tango.test_context import get_host_ip

from tests.utils import EventStore


def pytest_addoption(parser):
    "Add additional options"
    parser.addoption(
        "--event-storage-files-path",
        action="store",
        default=None,
        help="File path to store event tracking files to",
    )


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


@pytest.fixture(scope="function")
def event_store():
    """Fixture for storing events"""
    return EventStore()


@pytest.fixture(scope="function")
def event_store_class():
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
    return "mid-dish/dish-manager/SKA001"


@pytest.fixture
def ds_device_fqdn():
    return "mid-dish/ds-manager/SKA001"


@pytest.fixture
def spf_device_fqdn():
    return "mid-dish/simulator-spfc/SKA001"


@pytest.fixture
def spfrx_device_fqdn():
    return "mid-dish/simulator-spfrx/SKA001"


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


@dataclass
class TrackedDevice:
    """Class to group tracked device information"""

    device_proxy: tango.DeviceProxy
    attribute_names: Tuple[str]
    subscription_ids: List[int] = field(default_factory=list)


class EventPrinter:
    """Class that writes to attribte changes to a file"""

    def __init__(self, filename: str, tracked_devices: Tuple[TrackedDevice] = ()) -> None:
        self.tracked_devices = tracked_devices
        self.filename = filename

    def __enter__(self):
        for tracked_device in self.tracked_devices:
            dp = tracked_device.device_proxy
            for attr_name in tracked_device.attribute_names:
                sub_id = dp.subscribe_event(attr_name, tango.EventType.CHANGE_EVENT, self)
                tracked_device.subscription_ids.append(sub_id)

    def __exit__(self, exc_type, exc_value, exc_tb):
        for tracked_device in self.tracked_devices:
            try:
                dp = tracked_device.device_proxy
                for sub_id in tracked_device.subscription_ids:
                    dp.unsubscribe_event(sub_id)
            except tango.DevError:
                pass

    def push_event(self, ev: tango.EventData):
        with open(self.filename, "a", encoding="utf-8") as open_file:
            if ev.err:
                err = ev.errors[0]
                open_file.write(f"\nEvent Error {err.desc} {err.origin} {err.reason}")
            else:
                attr_name = ev.attr_name.split("/")[-1]
                attr_value = ev.attr_value.value
                if ev.attr_value.type == tango.CmdArgType.DevEnum:
                    attr_value = ev.device.get_attribute_config(attr_name).enum_labels[attr_value]

                open_file.write(
                    (f"\nEvent\t{ev.reception_date}\t{ev.device}" f"\t{attr_name}\t{attr_value}")
                )


@pytest.fixture(scope="function")
def monitor_tango_servers(request: pytest.FixtureRequest, dish_manager_proxy, ds_device_proxy):
    event_files_dir = request.config.getoption("--event-storage-files-path")
    if event_files_dir is None:
        yield None
        return

    if not os.path.exists(event_files_dir):
        os.makedirs(event_files_dir)

    file_name = ".".join((f"events_{request.node.name}", "txt"))
    file_path = os.path.join(event_files_dir, file_name)

    dm_tracker = TrackedDevice(
        dish_manager_proxy,
        (
            "dishmode",
            # "capturing", TODO push event is disabled
            "healthstate",
            "pointingstate",
            "b1capabilitystate",
            "b2capabilitystate",
            "b3capabilitystate",
            "b4capabilitystate",
            "b5acapabilitystate",
            "b5bcapabilitystate",
            "achievedtargetlock",
            "achievedpointing",
            "achievedpointingaz",
            "achievedpointingel",
            "configuredband",
            "spfconnectionstate",
            "spfrxconnectionstate",
            "dsconnectionstate",
            "longrunningcommandstatus",
            "longrunningcommandresult",
            "longrunningcommandprogress",
        ),
    )
    ds_tracker = TrackedDevice(
        ds_device_proxy,
        (
            "operatingMode",
            "powerState",
            "healthState",
            "pointingState",
            "indexerPosition",
            "achievedPointing",
            "achievedPointingaz",
            "achievedPointingel",
        ),
    )

    event_printer = EventPrinter(file_path, (dm_tracker, ds_tracker))
    with event_printer:
        with open(file_path, "a", encoding="utf-8") as open_file:
            open_file.write("\n\nEvents set up, test starting\n")
        yield
