"""Unit tests for subservient device connection states."""

import pytest
import tango
from ska_control_model import CommunicationStatus


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    ("sub_device, connection_state_attr"),
    [
        ("DS", "dsConnectionState"),
        ("SPFRX", "spfrxConnectionState"),
        ("SPF", "spfConnectionState"),
        ("WMS", "wmsConnectionState"),
        ("B5DC", "b5dcConnectionState"),
    ],
)
def test_connection_state_attrs_mirror_communication_status(
    dish_manager_resources,
    event_store_class,
    sub_device,
    connection_state_attr,
):
    device_proxy, dish_manager_cm = dish_manager_resources
    event_store = event_store_class()

    device_proxy.subscribe_event(
        connection_state_attr,
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    event_store.wait_for_value(CommunicationStatus.ESTABLISHED, timeout=10)

    # Force communication_state to NOT_ESTABLISHED
    sub_component_manager = dish_manager_cm.sub_component_managers[sub_device]
    sub_component_manager._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)

    # We can now expect connectionState to transition to NOT_ESTABLISHED
    event_store.wait_for_value(CommunicationStatus.NOT_ESTABLISHED)
