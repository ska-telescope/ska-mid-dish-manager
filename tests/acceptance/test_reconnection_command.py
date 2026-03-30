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

    ds_connection_state_event_store.wait_for_value(CommunicationStatus.ESTABLISHED, timeout=6)
    spf_connection_state_event_store.wait_for_value(CommunicationStatus.ESTABLISHED, timeout=6)
    spfrx_connection_state_event_store.wait_for_value(CommunicationStatus.ESTABLISHED, timeout=6)

    dish_manager_proxy.ResetSubsConnections(["DS", "SPF", "SPFRX"])

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
