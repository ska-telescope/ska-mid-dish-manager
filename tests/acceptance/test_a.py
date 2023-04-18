"""Test sleep"""
import pytest
import tango
from ska_control_model import CommunicationStatus

from tests.utils import EventStore


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_sleep(dish_manager_proxy, ds_device_proxy, spf_device_proxy, spfrx_device_proxy):
    """Test sleep"""
    print("BBBefore")
    print(dish_manager_proxy.getComponentStates())

    ds_event_store = EventStore()
    spf_event_store = EventStore()
    spfrx_event_store = EventStore()

    assert dish_manager_proxy.ping()
    assert ds_device_proxy.ping()
    assert spf_device_proxy.ping()
    assert spfrx_device_proxy.ping()

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

    assert ds_event_store.wait_for_value(CommunicationStatus.ESTABLISHED, timeout=30)
    assert spf_event_store.wait_for_value(CommunicationStatus.ESTABLISHED, timeout=30)
    assert spfrx_event_store.wait_for_value(CommunicationStatus.ESTABLISHED, timeout=30)

    print("AAAfter")
    print(dish_manager_proxy.getComponentStates())

    assert 0
