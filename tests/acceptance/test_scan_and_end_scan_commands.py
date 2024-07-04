"""Test the Scan and EndScan command"""

import pytest
import tango


# pylint: disable=too-many-locals,unused-argument
@pytest.mark.acceptance
@pytest.mark.forked
def test_scan_and_end_scan_commands(dish_manager_proxy, event_store_class):
    """Test Scan and EndScan command"""
    result_event_store = event_store_class()
    progress_event_store = event_store_class()
    attribute_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )
    dish_manager_proxy.subscribe_event(
        "scanID", tango.EventType.CHANGE_EVENT, attribute_event_store
    )

    # exercising scanID using the Scan and EndScan commands
    scan_id = "4"
    [[_], [unique_id]] = dish_manager_proxy.Scan(scan_id)
    result_event_store.wait_for_command_id(unique_id)
    progress_event_store.wait_for_progress_update("Scan completed")
    attribute_event_store.wait_for_value(scan_id)

    [[_], [unique_id]] = dish_manager_proxy.EndScan()
    result_event_store.wait_for_command_id(unique_id)
    progress_event_store.wait_for_progress_update("EndScan completed")
    assert dish_manager_proxy.read_attribute("scanID").value == ""

    # exercising scanID using the write method and EndScan command
    scan_id = "5"
    dish_manager_proxy.write_attribute("scanID", scan_id)
    attribute_event_store.wait_for_value(scan_id)

    [[_], [unique_id]] = dish_manager_proxy.EndScan()
    result_event_store.wait_for_command_id(unique_id)
    progress_event_store.wait_for_progress_update("EndScan completed")
    assert dish_manager_proxy.read_attribute("scanID").value == ""
