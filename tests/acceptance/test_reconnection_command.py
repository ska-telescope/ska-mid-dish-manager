"""Test reset connection command."""

from typing import Any

import pytest
import tango
from ska_control_model import CommunicationStatus

from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.mark.acceptance
def test_reset_connection_cmd(
    dish_manager_proxy: tango.DeviceProxy, event_store_class: Any
) -> None:
    """Test reseting of connection command."""
    ds_connection_state_event_store = event_store_class()
    spf_connection_state_event_store = event_store_class()
    spfrx_connection_state_event_store = event_store_class()

    attr_cb_mapping = {
        "dsConnectionState": ds_connection_state_event_store,
        "spfConnectionState": spf_connection_state_event_store,
        "spfrxConnectionState": spfrx_connection_state_event_store,
    }

    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    dish_manager_proxy.ResetSubsConnections(["DS", "SPF", "SPFRX"])

    # Stop_communicating sets connection state to disabled
    ds_connection_state_event_store.wait_for_value(CommunicationStatus.DISABLED, timeout=30)
    spf_connection_state_event_store.wait_for_value(CommunicationStatus.DISABLED, timeout=30)
    spfrx_connection_state_event_store.wait_for_value(CommunicationStatus.DISABLED, timeout=30)
    # Start_communicating sets connection state to not_established
    # and it the connectionstate is updated automatically to established
    ds_connection_state_event_store.wait_for_value(CommunicationStatus.NOT_ESTABLISHED, timeout=30)
    spf_connection_state_event_store.wait_for_value(
        CommunicationStatus.NOT_ESTABLISHED, timeout=30
    )
    spfrx_connection_state_event_store.wait_for_value(
        CommunicationStatus.NOT_ESTABLISHED, timeout=30
    )

    ds_connection_state_event_store.wait_for_value(CommunicationStatus.ESTABLISHED, timeout=60)
    spf_connection_state_event_store.wait_for_value(CommunicationStatus.ESTABLISHED, timeout=60)
    spfrx_connection_state_event_store.wait_for_value(CommunicationStatus.ESTABLISHED, timeout=60)

    remove_subscriptions(subscriptions)
