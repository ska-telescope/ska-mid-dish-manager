"""Contains pytest fixtures for other tests setup."""

import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pytest
from ska_tango_event_monitor import QueryEventSystemResponse, ResponseChangeSummary
from ska_tango_event_monitor.render import render_report
from tango import ApiUtil, DeviceProxy, Group

from ska_mid_dish_manager.models.constants import (
    DEFAULT_B5DC_PROXY_TRL,
    DEFAULT_DISH_MANAGER_TRL,
    DEFAULT_DS_MANAGER_TRL,
    DEFAULT_SPFC_TRL,
    DEFAULT_SPFRX_TRL,
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
    parser.addoption(
        "--event-diag-file-dir",
        action="store",
        default=None,
        help="File path to store event diagnostic data.",
    )
    parser.addoption(
        "--track-device-events",
        action="append",
        default=[],
        help="List of device names to track events for.",
    )


@pytest.fixture
def event_tracking_record_file(request) -> Optional[Path]:
    """Creates a file path if specified and it does not exist."""
    now = datetime.now(timezone.utc)
    events_path_dir = request.config.getoption("--event-diag-file-dir")
    if not events_path_dir:
        return None
    if not os.path.exists(os.path.dirname(events_path_dir)):
        os.makedirs(os.path.dirname(events_path_dir), exist_ok=True)
    file_name = f"{now.timestamp()}_event_diag_{request.node.name}.txt"
    file_name = file_name.replace("/", "_").replace("\\", "_").replace("]", "_").replace("[", "_")
    file_path = Path(events_path_dir).joinpath(file_name)
    return file_path


@pytest.fixture(scope="session")
def session_event_tracking_record_file(request) -> Optional[Path]:
    """Creates a file path if specified and it does not exist."""
    events_path_dir = request.config.getoption("--event-diag-file-dir")
    if not events_path_dir:
        return None
    if not os.path.exists(os.path.dirname(events_path_dir)):
        os.makedirs(os.path.dirname(events_path_dir), exist_ok=True)
    file_name = "test_session_stats.txt"
    file_path = Path(events_path_dir).joinpath(file_name)
    return file_path


@pytest.fixture()
def is_acceptance_test(request) -> bool:
    """Returns whether this is an acceptance test or not."""
    marker_names = [marker.name for marker in request.node.iter_markers()]
    if "unit" in marker_names:
        return False
    if "unit" in request.node.nodeid:
        return False
    return "acceptance" in marker_names


@pytest.fixture(scope="session")
def is_acceptance_test_session(request) -> bool:
    """Returns whether this is an acceptance test or not."""
    marker_names = [marker.name for marker in request.node.iter_markers()]
    if "unit" in marker_names:
        return False
    if "unit" in request.node.nodeid:
        return False
    return "acceptance" in marker_names


@pytest.fixture
def event_tracking_device_group(request, is_acceptance_test) -> Optional[Group]:
    """Creates a Tango device group of the associated admin devices."""
    if not is_acceptance_test:
        return None
    trls = request.config.getoption("--track-device-events")
    if not trls:
        return None
    group = Group("EventTrackingGroup")
    for trl in trls:
        dp = DeviceProxy(trl)
        group.add(dp.adm_name())
    return group


@pytest.fixture(scope="session")
def event_tracking_device_group_session(request, is_acceptance_test_session) -> Optional[Group]:
    """Creates a Tango device group of the associated admin devices."""
    if not is_acceptance_test_session:
        return None
    trls = request.config.getoption("--track-device-events")
    if not trls:
        return None
    group = Group("EventTrackingGroup")
    for trl in trls:
        dp = DeviceProxy(trl)
        group.add(dp.adm_name())
    return group


@pytest.fixture(autouse=True)
def enable_event_tracking(
    request, is_acceptance_test, event_tracking_device_group, event_tracking_record_file
):
    """Enable event tracking for acceptance tests."""
    if is_acceptance_test and event_tracking_device_group and event_tracking_record_file:
        tracking_enabled = getattr(request.node, "tracking_enabled", False)
        if not tracking_enabled:
            ApiUtil.instance().enable_event_system_perf_mon(True)
            event_tracking_device_group.command_inout("EnableEventSystemPerfMon", True)
            request.node.tracking_enabled = True
    yield


@dataclass
class EventTrackingData:
    """Data class to hold event tracking data."""

    event_data_before: str
    event_data_after: str

    def render_tracking_summary(self) -> str:
        """Render the event tracking data diff as a string."""
        assert self.event_data_before is not None, "Event data before test is None"
        assert self.event_data_after is not None, "Event data after test is None"

        before_response = QueryEventSystemResponse.from_json(json.loads(self.event_data_before))
        after_response = QueryEventSystemResponse.from_json(json.loads(self.event_data_after))
        return render_report(ResponseChangeSummary.from_responses(after_response, before_response))


@pytest.fixture(autouse=True)
def add_test_event_info_and_time(
    request, is_acceptance_test, event_tracking_device_group, event_tracking_record_file
):
    """Record the event diagnostics per test in event-diag-file-path."""
    if is_acceptance_test and event_tracking_device_group and event_tracking_record_file:
        device_event_info: dict[str, EventTrackingData] = {}
        test_event_info: EventTrackingData = EventTrackingData(
            event_data_before=ApiUtil.instance().query_event_system(), event_data_after=""
        )
        with event_tracking_record_file.open(mode="a", encoding="utf-8") as f:
            start = datetime.now(timezone.utc)
            f.write("\n*******************\n")
            f.write(f"\nSTART [{request.node.nodeid}] at [{start.isoformat()}]\n")
            f.write("\n*******************\n")
            replies = event_tracking_device_group.command_inout("QueryEventSystem")
            for reply in replies:
                name = reply.dev_name()
                device_event_info[name] = EventTrackingData(
                    event_data_before=reply.get_data(), event_data_after=""
                )

    yield

    if is_acceptance_test and event_tracking_device_group and event_tracking_record_file:
        test_event_info.event_data_after = ApiUtil.instance().query_event_system()
        with event_tracking_record_file.open(mode="a", encoding="utf-8") as f:
            replies = event_tracking_device_group.command_inout("QueryEventSystem")
            for reply in replies:
                name = reply.dev_name()
                device_event_info[name].event_data_after = reply.get_data()
            for name, data in device_event_info.items():
                f.write(f"\n\nDevice Summary: {name}\n\n")
                f.write(data.render_tracking_summary())
            f.write("\n\nTest Summary:\n\n")
            f.write(test_event_info.render_tracking_summary())
            end = datetime.now(timezone.utc)
            f.write(f"\n\nEND [{request.node.nodeid}] at [{end.isoformat()}]\n")


@pytest.fixture(scope="session", autouse=True)
def add_test_event_info_and_time_per_session(
    request,
    is_acceptance_test_session,
    event_tracking_device_group_session,
    session_event_tracking_record_file,
):
    """Record the event diagnostics per test in event-diag-file-path."""
    if (
        is_acceptance_test_session
        and event_tracking_device_group_session
        and session_event_tracking_record_file
    ):
        device_event_info: dict[str, EventTrackingData] = {}
        test_event_info: EventTrackingData = EventTrackingData(
            event_data_before=ApiUtil.instance().query_event_system(), event_data_after=""
        )
        with session_event_tracking_record_file.open(mode="a", encoding="utf-8") as f:
            start = datetime.now(timezone.utc)
            f.write("\n*******************\n")
            f.write(f"\nSESSION START [{request.node.nodeid}] at [{start.isoformat()}]\n")
            f.write("\n*******************\n")
            replies = event_tracking_device_group_session.command_inout("QueryEventSystem")
            for reply in replies:
                name = reply.dev_name()
                device_event_info[name] = EventTrackingData(
                    event_data_before=reply.get_data(), event_data_after=""
                )

    yield

    if (
        is_acceptance_test_session
        and event_tracking_device_group_session
        and session_event_tracking_record_file
    ):
        test_event_info.event_data_after = ApiUtil.instance().query_event_system()
        with session_event_tracking_record_file.open(mode="a", encoding="utf-8") as f:
            replies = event_tracking_device_group_session.command_inout("QueryEventSystem")
            for reply in replies:
                name = reply.dev_name()
                device_event_info[name].event_data_after = reply.get_data()
            for name, data in device_event_info.items():
                f.write(f"\n\nDevice Summary: {name}\n\n")
                f.write(data.render_tracking_summary())
            f.write("\n\nSession Test Summary:\n\n")
            f.write(test_event_info.render_tracking_summary())
            end = datetime.now(timezone.utc)
            f.write(f"\n\nEND [{request.node.nodeid}] at [{end.isoformat()}]\n")


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
def b5dc_device_fqdn():
    return DEFAULT_B5DC_PROXY_TRL
