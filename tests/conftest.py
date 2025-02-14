"""Contains pytest fixtures for other tests setup"""

# pylint: disable=too-many-statements,invalid-name,missing-function-docstring,redefined-outer-name

import os
import socket
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Tuple

import pytest
import tango
from tango.test_context import get_host_ip

from ska_mid_dish_manager.models.constants import (
    DEFAULT_DISH_MANAGER_TRL,
    DEFAULT_DS_MANAGER_TRL,
    DEFAULT_SPFC_TRL,
    DEFAULT_SPFRX_TRL,
)
from tests.utils import ComponentStateStore, EventStore


def pytest_addoption(parser):
    "Add additional options"
    parser.addoption(
        "--event-storage-files-path",
        action="store",
        default=None,
        help="File path to store event tracking files to",
    )
    parser.addoption(
        "--zmq-events-path",
        action="store",
        default=None,
        help="File path to store zmq events",
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
    return ComponentStateStore()


@pytest.fixture
def dish_manager_device_fqdn():
    return DEFAULT_DISH_MANAGER_TRL


@pytest.fixture
def ds_device_fqdn():
    return DEFAULT_DS_MANAGER_TRL


@pytest.fixture
def spf_device_fqdn():
    return DEFAULT_SPFC_TRL


@pytest.fixture
def spfrx_device_fqdn():
    return DEFAULT_SPFRX_TRL


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
            "configuretargetlock",
            "achievedpointing",
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
            "achievedTargetLock",
            "configureTargetLock",
        ),
    )

    event_printer = EventPrinter(file_path, (dm_tracker, ds_tracker))
    with event_printer:
        with open(file_path, "a", encoding="utf-8") as open_file:
            open_file.write("\n\nEvents set up, test starting\n")
        yield


# pylint: disable=line-too-long,unspecified-encoding
@pytest.fixture
def record_event_from_zmq(request):
    event_files_dir = request.config.getoption("--zmq-events-path")
    if not os.path.exists(event_files_dir):
        os.makedirs(event_files_dir)

    file_name = ".".join((f"events_{request.node.name}", "json"))
    file_path = os.path.join(event_files_dir, file_name)

    dp = tango.DeviceProxy("mid-dish/dish-manager/SKA001")
    if dp.info().dev_class != "DServer":
        adm_name = dp.adm_name()
        dp = tango.DeviceProxy(adm_name)

    if "QueryEventSystem" not in dp.get_command_list():
        pytest.fail("QueryEventSystem command not available in the device")

    # Function to monitor the event system
    def monitor_event_system(stop_event):
        with open(file_path, "a") as f:
            dp.StartEventSystemPerfMon()
            while not stop_event.is_set():
                next_poll = time.time() + 10
                try:
                    data = dp.QueryEventSystem()
                    f.write(
                        f'{{"time":"{datetime.now().isoformat()}","name":"{adm_name}","data":{data}}}\n'  # noqa: E501
                    )
                except tango.DevFailed as exc:
                    print(exc, file=sys.stderr)
                    f.write(
                        f'{{"time":"{datetime.now().isoformat()}","name":"{adm_name}","error":"{repr(exc)}"}}\n'  # noqa: E501
                    )

                f.flush()
                sleep_for = next_poll - time.time()
                if sleep_for > 0.001:
                    time.sleep(sleep_for)
                elif sleep_for < 0:
                    print(f"poll time missed by {-sleep_for}s", file=sys.stderr)

            dp.StopEventSystemPerfMon()

    # Create a thread to run the monitoring function
    stop_event = threading.Event()
    monitor_thread = threading.Thread(target=monitor_event_system, args=(stop_event,))
    monitor_thread.start()

    # Teardown function to stop the monitoring and clean up
    def cleanup():
        stop_event.set()
        monitor_thread.join()
        dp.StopEventSystemPerfMon()

    request.addfinalizer(cleanup)

    return file_path
