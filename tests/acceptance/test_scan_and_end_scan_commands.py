"""Test the Scan and EndScan command."""

import pytest

from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.mark.acceptance
def test_scan_and_end_scan_commands(dish_manager_proxy, event_store_class):
    """Test Scan and EndScan command."""
    attribute_event_store = event_store_class()
    attr_cb_mapping = {
        "scanID": attribute_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    # exercising scanID using the Scan and EndScan commands
    scan_id = "4"
    [[_], [msg]] = dish_manager_proxy.Scan(scan_id)
    assert msg == "Scan ID set to 4"
    assert dish_manager_proxy.read_attribute("scanID").value == scan_id
    attribute_event_store.wait_for_value(scan_id, timeout=5)

    [[_], [msg]] = dish_manager_proxy.EndScan()
    assert msg == "Scan ID cleared"
    assert dish_manager_proxy.read_attribute("scanID").value == ""

    # exercising scanID using the write method and EndScan command
    scan_id = "5"
    dish_manager_proxy.write_attribute("scanID", scan_id)
    attribute_event_store.wait_for_value(scan_id, timeout=5)

    dish_manager_proxy.EndScan()
    assert dish_manager_proxy.read_attribute("scanID").value == ""

    remove_subscriptions(subscriptions)
