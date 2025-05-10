"""Test reconnection and error event handling"""

import time

import pytest
import tango
from ska_control_model import CommunicationStatus

from tests.utils import wait_for_attribute_value


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

    alarm_status_msg = (
        "Event channel on a sub-device is not responding "
        "anymore or change event subscription is not complete"
    )
    normal_status_msg = "The device is in ON state."

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

    # restart the sub-component device
    device = tango.DeviceProxy(f"mid-dish/{family}/SKA001")
    admin_device = tango.DeviceProxy(device.adm_name())
    admin_device.RestartServer()

    # check dish manager reported the correct states when the device died
    conn_state_event_store.wait_for_value(CommunicationStatus.NOT_ESTABLISHED, timeout=60)
    state_event_store.wait_for_value(tango.DevState.ALARM, timeout=60)
    status_event_store.wait_for_value(alarm_status_msg, timeout=60)

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
            time.sleep(0.5)

    # check that dish manager reports the correct states after the device restarts
    wait_for_attribute_value(
        dish_manager_proxy,
        family_attr_mapping[family],
        CommunicationStatus.ESTABLISHED,
        conn_state_event_store,
        timeout=60,
    )
    wait_for_attribute_value(
        dish_manager_proxy, "State", tango.DevState.ON, state_event_store, timeout=60
    )
    wait_for_attribute_value(
        dish_manager_proxy, "Status", normal_status_msg, status_event_store, timeout=60
    )
