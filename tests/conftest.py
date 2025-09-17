"""Contains pytest fixtures for other tests setup."""

import logging
import os
import socket
import threading
import time
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import List, Tuple

import pytest
import tango
from matplotlib import pyplot as plt
from tango.test_context import get_host_ip

from ska_mid_dish_manager.models.constants import (
    DEFAULT_DISH_MANAGER_TRL,
    DEFAULT_DS_MANAGER_TRL,
    DEFAULT_SPFC_TRL,
    DEFAULT_SPFRX_TRL,
    DEFAULT_WMS_TRL,
)
from tests.utils import ComponentStateStore, EventStore

LOGGER = logging.getLogger(__name__)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Log remaining threads at the end."""
    time.sleep(1)
    threads = threading.enumerate()
    for t in threads:
        LOGGER.info(
            "  - %s (Alive: %s, ident=%s, daemon=%s)", t.name, t.is_alive(), t.ident, t.daemon
        )
        if t is threading.main_thread():
            continue

    assert len(threads) == 1, "Unexpected threads remaining after tests"



def pytest_addoption(parser):
    """Add additional options."""
    parser.addoption(
        "--event-storage-files-path",
        action="store",
        default=None,
        help="File path to store event tracking files to",
    )
    parser.addoption(
        "--pointing-files-path",
        action="store",
        default=None,
        help="File path to store pointing files to when tests have the required fixture",
    )


@pytest.fixture(scope="module", name="open_port")
def get_open_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
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


@pytest.fixture
def event_store():
    """Fixture for storing events."""
    return EventStore()


@pytest.fixture
def event_store_class():
    """Fixture for storing events."""
    return EventStore


@pytest.fixture
def component_state_store():
    """Fixture for storing component state changes over time."""
    return ComponentStateStore()


@pytest.fixture(scope="session")
def dish_manager_device_fqdn():
    return DEFAULT_DISH_MANAGER_TRL


@pytest.fixture(scope="session")
def ds_device_fqdn():
    return DEFAULT_DS_MANAGER_TRL


@pytest.fixture(scope="session")
def spf_device_fqdn():
    return DEFAULT_SPFC_TRL


@pytest.fixture(scope="session")
def spfrx_device_fqdn():
    return DEFAULT_SPFRX_TRL


@pytest.fixture(scope="session")
def wms_device_fqdn():
    return DEFAULT_WMS_TRL


@pytest.fixture(scope="module")
def dish_manager_proxy(dish_manager_device_fqdn):
    dev_proxy = tango.DeviceProxy(dish_manager_device_fqdn)
    # increase client request timeout to 5 seconds
    dev_proxy.set_timeout_millis(10000)
    return dev_proxy


@pytest.fixture(scope="module")
def ds_device_proxy(ds_device_fqdn):
    dev_proxy = tango.DeviceProxy(ds_device_fqdn)
    # increase client request timeout to 5 seconds
    dev_proxy.set_timeout_millis(10000)
    return dev_proxy


@pytest.fixture(scope="module")
def spf_device_proxy(spf_device_fqdn):
    return tango.DeviceProxy(spf_device_fqdn)


@pytest.fixture(scope="module")
def spfrx_device_proxy(spfrx_device_fqdn):
    return tango.DeviceProxy(spfrx_device_fqdn)


@pytest.fixture(scope="module")
def wms_device_proxy(wms_device_fqdn):
    return tango.DeviceProxy(wms_device_fqdn)


@dataclass
class TrackedDevice:
    """Class to group tracked device information."""

    device_proxy: tango.DeviceProxy
    attribute_names: Tuple[str]
    subscription_ids: List[int] = field(default_factory=list)


class EventPrinter:
    """Class that writes to attribte changes to a file."""

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
                    (f"\nEvent\t{ev.reception_date}\t{ev.device}\t{attr_name}\t{attr_value}")
                )


@pytest.fixture
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
            "capturing",
            "healthstate",
            "pointingstate",
            "b1capabilitystate",
            "b2capabilitystate",
            "b3capabilitystate",
            "b4capabilitystate",
            "b5acapabilitystate",
            "b5bcapabilitystate",
            "achievedtargetlock",
            "dsccmdauth",
            "dscctrlstate",
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
            "dscCmdAuth",
            "dscCtrlState",
            "configureTargetLock",
        ),
    )

    max_retries = 5
    retry_delay = 1  # seconds

    for attempt in range(max_retries):
        try:
            event_printer = EventPrinter(file_path, (dm_tracker, ds_tracker))
            event_printer.__enter__()  # manually enter to handle retries
            break  # success, exit retry loop
        except tango.DevFailed as e:
            if attempt < max_retries - 1:
                print(f"Subscription attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                print(f"Failed to subscribe to events after {max_retries} attempts: {e}")
                event_printer = None

    if event_printer is not None:
        with open(file_path, "a", encoding="utf-8") as open_file:
            open_file.write("\n\nEvents set up, test starting\n")
        try:
            yield
        finally:
            event_printer.__exit__(None, None, None)
    else:
        yield  # continue without event tracking if subscriptions failed



@pytest.fixture
def plot_dish_manager_pointing(
    request: pytest.FixtureRequest, dish_manager_proxy: tango.DeviceProxy
) -> Generator:
    """Monitor achievedPointing and plot a graph of the values over the test execution."""
    file_storage_dir = request.config.getoption("--pointing-files-path")

    if file_storage_dir is None:
        yield None
        return

    if not os.path.exists(file_storage_dir):
        os.makedirs(file_storage_dir)

    data_rows = []

    def capture_achievedPointing_cb(tango_event: tango.EventData) -> None:
        if tango_event.attr_value:
            val = tango_event.attr_value.value
            data_rows.append(val)

    sub_id = dish_manager_proxy.subscribe_event(
        "achievedpointing", tango.EventType.ARCHIVE_EVENT, capture_achievedPointing_cb, []
    )

    yield

    dish_manager_proxy.unsubscribe_event(sub_id)

    if data_rows:
        plot_name = ".".join((f"pointing_plot_{request.node.name}", "png"))
        plot_file_path = os.path.join(file_storage_dir, plot_name)

        fig, (timestamp_ax, azel_ax) = plt.subplots(2, 1, figsize=(10, 8))

        tai_list, az_list, el_list = zip(*data_rows)

        timestamp_ax.plot(tai_list, az_list, label="Azimuth")
        timestamp_ax.plot(tai_list, el_list, label="Elevation")
        timestamp_ax.set_title("Axis vs Time")
        timestamp_ax.set_ylabel("Position (degrees)")
        timestamp_ax.legend()

        azel_ax.plot(az_list, el_list)
        azel_ax.set_title("Azimuth vs Elevation")
        azel_ax.set_xlabel("Azimuth (degrees)")
        azel_ax.set_ylabel("Elevation (degrees)")

        fig.savefig(plot_file_path)
