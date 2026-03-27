"""Test connection verification."""

import pytest
from ska_control_model import CommunicationStatus

from ska_mid_dish_manager.component_managers.device_proxy_factory import DeviceProxyManager
from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.mark.acceptance
def test_connection_verification_recovers_device(
    event_store_class,
    dish_manager_proxy,
):
    """Test that connection verification recovers after device restart."""
    dp_manager = DeviceProxyManager()

    # Tracking the state connection
    conn_state_event_store = event_store_class()

    attr_cb_mapping = {
        "spfConnectionState": conn_state_event_store,
    }

    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    # SPFC device proxy
    device_proxy = dp_manager("mid-dish/simulator-spfc/SKA001")
    admin_device_proxy = dp_manager(device_proxy.adm_name())

    # Restart device to trigger API_EventTimeout
    admin_device_proxy.RestartServer()

    # Wait for system to detect issue
    conn_state_event_store.wait_for_value(
        CommunicationStatus.NOT_ESTABLISHED,
        timeout=30,
    )

    # Wait for device to come back
    dp_manager.wait_for_device(device_proxy)

    # Verify recovery
    conn_state_event_store.wait_for_value(
        CommunicationStatus.ESTABLISHED,
        timeout=30,
    )

    remove_subscriptions(subscriptions)
