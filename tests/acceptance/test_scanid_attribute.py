"""Test the scanid attribute"""
import pytest
import tango


# pylint: disable=too-many-locals,unused-argument
@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_scanid_attribute(dish_manager_proxy, event_store_class):
    """Test scanid attribute"""
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
    scan_id = "5"
    dish_manager_proxy.write_attribute("scanID", scan_id)
    dm_model_event_store.wait_for_value(scan_id)

    [[_], [unique_id]] = dish_manager_proxy.EndScan()
    progress_event_store.wait_for_progress_update("EndScan completed")
    result_event_store.wait_for_command_id(unique_id)
    dm_model_event_store.wait_for_value(scan_id)
