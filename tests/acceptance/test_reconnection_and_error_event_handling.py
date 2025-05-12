"""Test reconnection and error event handling"""

import time

import pytest
import tango
from ska_control_model import CommunicationStatus


@pytest.mark.xfail(reason="This test is flaky: needs investigation into events and timeouts")
@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.parametrize("family", ["ds-manager", "simulator-spfc", "simulator-spfrx"])
def test_device_goes_away(family, event_store_class, dish_manager_proxy):
    """Test dish manager reacts to devices restarting"""
    family_attr_mapping = {
        "ds-manager": "dsConnectionState",
        "simulator-spfc": "spfConnectionState",
        "simulator-spfrx": "spfrxConnectionState",
    }

    conn_state_event_store = event_store_class()
    state_event_store = event_store_class()
    status_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "State",
        tango.EventType.CHANGE_EVENT,
        state_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "Status",
        tango.EventType.CHANGE_EVENT,
        status_event_store,
    )

    dish_manager_proxy.subscribe_event(
        family_attr_mapping[family],
        tango.EventType.CHANGE_EVENT,
        conn_state_event_store,
    )

    # clear the event store queues to remove initial values on subscription
    conn_state_event_store.clear_queue()
    state_event_store.clear_queue()
    status_event_store.clear_queue()
    dummy_event_store = event_store_class()

    # restart the sub-component device
    device = tango.DeviceProxy(f"mid-dish/{family}/SKA001")
    admin_device = tango.DeviceProxy(device.adm_name())
    admin_device.RestartServer()

    alarm_status_msg = (
        "Event channel on a sub-device is not responding "
        "anymore or change event subscription is not complete"
    )
    normal_status_msg = "The device is in ON state."

    # check dish manager reported the correct states when the device died
    conn_state_event_store.wait_for_value(CommunicationStatus.NOT_ESTABLISHED, timeout=30)
    state_event_store.wait_for_value(tango.DevState.ALARM, timeout=30)
    status_event_store.wait_for_value(alarm_status_msg, timeout=30)

    # wait for the device to come back online
    start_time = time.time()
    while True:
        if time.time() - start_time > 60:
            # if the device is unreachable after 60 seconds of restart, we can break the loop
            break
        try:
            device.ping()
            # if the device is reachable, we can break the loop
            break
        except tango.DevFailed:
            dummy_event_store.get_queue_values()

    # check dish manager reports normal states after the device is restarted
    conn_state_event_store.wait_for_value(CommunicationStatus.ESTABLISHED, timeout=30)
    state_event_store.wait_for_value(tango.DevState.ON, timeout=30)
    status_event_store.wait_for_value(normal_status_msg, timeout=30)
