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


@pytest.mark.unit
@pytest.mark.forked
def test_dsc_connection_state_attr_updates(
    dish_manager_resources,
    event_store_class,
):
    """Test dscConnectionState updates when DS connectionState updates."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_event_store = event_store_class()
    dsc_event_store = event_store_class()

    device_proxy.subscribe_event(
        "dsConnectionState",
        tango.EventType.CHANGE_EVENT,
        ds_event_store,
    )

    device_proxy.subscribe_event(
        "dscConnectionState",
        tango.EventType.CHANGE_EVENT,
        dsc_event_store,
    )
    ds_event_store.wait_for_value(CommunicationStatus.ESTABLISHED, timeout=10)
    dsc_event_store.wait_for_value(CommunicationStatus.DISABLED, timeout=10)

    # Force ds connectionstate to ESTABLISHED
    sub_component_manager = dish_manager_cm.sub_component_managers["DS"]
    sub_component_manager._update_component_state(connectionstate=CommunicationStatus.ESTABLISHED)

    # We can now expect dscConnectionState to transition to ESTABLISHED
    dsc_event_store.wait_for_value(CommunicationStatus.ESTABLISHED, timeout=10)


@pytest.mark.unit
@pytest.mark.forked
def test_dsc_connection_state_attr_updates_when_ds_connection_lost(
    dish_manager_resources,
    event_store_class,
):
    """Test dscConnectionState updates when ds communication is lost."""
    device_proxy, dish_manager_cm = dish_manager_resources
    event_store = event_store_class()

    device_proxy.subscribe_event(
        "dscConnectionState",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    event_store.wait_for_value(CommunicationStatus.DISABLED, timeout=10)

    # Force communication_state to NOT_ESTABLISHED
    sub_component_manager = dish_manager_cm.sub_component_managers["DS"]
    sub_component_manager._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)

    # We can now expect dscConnectionState to transition to NOT_ESTABLISHED
    event_store.wait_for_value(CommunicationStatus.NOT_ESTABLISHED)


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "connection_state_attr",
    [
        "wmsConnectionState",
        "b5dcConnectionState",
    ],
)
def test_connection_state_attrs_on_devices_with_no_monitoring(
    dish_manager_resources,
    event_store_class,
    connection_state_attr,
):
    device_proxy, _ = dish_manager_resources
    event_store = event_store_class()

    device_proxy.subscribe_event(
        connection_state_attr,
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    event_store.wait_for_value(CommunicationStatus.DISABLED, timeout=10)


@pytest.mark.unit
@pytest.mark.forked
def test_b5dc_server_connection_state_attr_updates(
    dish_manager_resources,
    event_store_class,
):
    """Test b5dcServerConnectionState updates when DS connectionState updates."""
    device_proxy, dish_manager_cm = dish_manager_resources
    b5_conn_state_event_store = event_store_class()
    b5_server_conn_event_store = event_store_class()

    device_proxy.subscribe_event(
        "b5dcConnectionState",
        tango.EventType.CHANGE_EVENT,
        b5_conn_state_event_store,
    )

    device_proxy.subscribe_event(
        "b5dcServerConnectionState",
        tango.EventType.CHANGE_EVENT,
        b5_server_conn_event_store,
    )
    b5_conn_state_event_store.wait_for_value(CommunicationStatus.ESTABLISHED, timeout=10)
    b5_server_conn_event_store.wait_for_value(CommunicationStatus.DISABLED, timeout=10)

    # Force B5dc Server connectionstate to ESTABLISHED
    sub_component_manager = dish_manager_cm.sub_component_managers["B5DC"]
    sub_component_manager._update_component_state(connectionstate=CommunicationStatus.ESTABLISHED)

    b5_server_conn_event_store.wait_for_value(CommunicationStatus.ESTABLISHED, timeout=10)


@pytest.mark.unit
@pytest.mark.forked
def test_b5dc_server_connection_state_attr_updates_when_b5dc_proxy_connection_lost(
    dish_manager_resources,
    event_store_class,
):
    """Test b5dcServerConnectionState updates when B5dc proxy communication is lost."""
    device_proxy, dish_manager_cm = dish_manager_resources
    event_store = event_store_class()

    device_proxy.subscribe_event(
        "b5dcConnectionState",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    event_store.wait_for_value(CommunicationStatus.DISABLED, timeout=10)

    # Force communication_state to NOT_ESTABLISHED
    sub_component_manager = dish_manager_cm.sub_component_managers["B5DC"]
    sub_component_manager._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)

    event_store.wait_for_value(CommunicationStatus.NOT_ESTABLISHED)
