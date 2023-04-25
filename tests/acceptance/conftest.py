"""Fixtures for running ska-mid-dish-manager acceptance tests"""

import pytest
import tango
from ska_control_model import CommunicationStatus

from ska_mid_dish_manager.models.dish_enums import DishMode
from tests.utils import EventStore


@pytest.fixture(autouse=True)
def setup_and_teardown(
    event_store,
    dish_manager_proxy,
    ds_device_proxy,
    spf_device_proxy,
    spfrx_device_proxy,
):
    """Reset the tango devices to a fresh state before each test"""

    assert ds_device_proxy.ping()
    assert spf_device_proxy.ping()
    assert spfrx_device_proxy.ping()

    ds_event_store = EventStore()
    spf_event_store = EventStore()
    spfrx_event_store = EventStore()

    dish_manager_proxy.subscribe_event(
        "dsConnectionState",
        tango.EventType.CHANGE_EVENT,
        ds_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "spfConnectionState",
        tango.EventType.CHANGE_EVENT,
        spf_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "spfrxConnectionState",
        tango.EventType.CHANGE_EVENT,
        spfrx_event_store,
    )

    assert ds_event_store.wait_for_value(CommunicationStatus.ESTABLISHED)
    assert spf_event_store.wait_for_value(CommunicationStatus.ESTABLISHED)
    assert spfrx_event_store.wait_for_value(CommunicationStatus.ESTABLISHED)

    ds_device_proxy.ResetToDefault()
    spf_device_proxy.ResetToDefault()
    spfrx_device_proxy.ResetToDefault()

    dish_manager_proxy.SyncComponentStates()

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    assert event_store.wait_for_value(DishMode.STANDBY_LP)

    yield
