"""Contains pytest fixtures for other tests setup."""

import logging
import threading
import time
from datetime import datetime, timezone

import pytest
from tango import ApiUtil

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


@pytest.fixture(autouse=True)
def add_test_event_info_and_time(request):
    """Print test information for acceptance tests."""
    markers = [mark.name for mark in request.node.iter_markers()]
    start = datetime.now(timezone.utc)
    print(f"\n[{start.isoformat()}] START {request.node.nodeid}")
    if "acceptance" in markers:
        api_util = ApiUtil.instance()
        event_info = api_util.query_event_system()
        print(f"Event info before the test: {event_info}")
    else:
        print(f"Markers for the test: {markers}")
    yield
    end = datetime.now(timezone.utc)
    print(f"[{end.isoformat()}] END   {request.node.nodeid}(duration: {end - start})")
    if "acceptance" in markers:
        api_util = ApiUtil.instance()
        event_info = api_util.query_event_system()
        print(f"Event info after the test: {event_info}")


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
