"""Test the SCAN command"""
import pytest
import tango


# pylint: disable=too-many-locals,unused-argument
@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_scan(dish_manager_proxy, event_store_class):
    """Test SCAN command"""
    result_event_store = event_store_class()
    progress_event_store = event_store_class()
    dm_model_event_store = event_store_class()

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
    scan_id = "4"
    [[_], [unique_id]] = dish_manager_proxy.Scan(scan_id)
    result_event_store.wait_for_command_id(unique_id)

    progress_event_store.wait_for_progress_update("Scan completed")
    dm_model_event_store.wait_for_value(scan_id)
