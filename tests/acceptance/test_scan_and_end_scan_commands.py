"""Test the Scan and EndScan command"""
import pytest
import tango


# pylint: disable=too-many-locals,unused-argument
@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_scan_and_end_scan_commands(dish_manager_proxy, event_store_class):
    """Test Scan and EndScan command"""
    result_event_store = event_store_class()
    progress_event_store = event_store_class()
    dm_model_event_store = event_store_class()
    model_event_store = event_store_class()
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
        "scanID", tango.EventType.CHANGE_EVENT, dm_model_event_store
    )
    dish_manager_proxy.subscribe_event("scanID", tango.EventType.CHANGE_EVENT, model_event_store)
    dish_manager_proxy.subscribe_event(
        "scanID", tango.EventType.CHANGE_EVENT, attribute_event_store
    )

    scan_id = "4"
    [[_], [unique_id]] = dish_manager_proxy.Scan(scan_id)
    result_event_store.wait_for_command_id(unique_id)

    progress_event_store.wait_for_progress_update("Scan completed")
    dm_model_event_store.wait_for_value(scan_id)

    [[_], [unique_id]] = dish_manager_proxy.EndScan()
    result_event_store.wait_for_command_id(unique_id)
    progress_event_store.wait_for_progress_update("EndScan completed")
    model_event_store.wait_for_value(scan_id)

    scan_id = "5"
    dish_manager_proxy.write_attribute("scanID", scan_id)
    attribute_event_store.wait_for_value(scan_id)

    [[_], [unique_id]] = dish_manager_proxy.EndScan()
    result_event_store.wait_for_command_id(unique_id)
    progress_event_store.wait_for_progress_update("EndScan completed")
    model_event_store.wait_for_value(scan_id)
