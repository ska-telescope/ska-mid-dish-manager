"""Test reset connection command."""

from typing import Any

import pytest
import tango
from ska_control_model import CommunicationStatus

from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.mark.acceptance
@pytest.mark.parametrize(
    "dev_name",
    [
        "spf",
        "spfrx",
        "ds",
    ],
)
def test_reset_connection_cmd(
    dish_manager_proxy: tango.DeviceProxy,
    event_store_class: Any,
    dev_name: str,
) -> None:
    """Test reseting of connection command."""
    connection_state_event_store = event_store_class()

    attr_cb_mapping = {
        f"{dev_name}ConnectionState": connection_state_event_store,
    }

    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    dish_manager_proxy.ResetComponentConnection(dev_name)

    # Stop_communicating sets connection state to disabled
    connection_state_event_store.wait_for_value(CommunicationStatus.DISABLED, timeout=30)

    # Start_communicating sets connection state to not_established
    # and it the connectionstate is updated automatically to established
    connection_state_event_store.wait_for_value(CommunicationStatus.NOT_ESTABLISHED, timeout=30)

    connection_state_event_store.wait_for_value(CommunicationStatus.ESTABLISHED, timeout=60)

    remove_subscriptions(subscriptions)
