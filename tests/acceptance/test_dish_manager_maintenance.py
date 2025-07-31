"""Test Maintenance Mode."""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode

WAIT_FOR_RESULT_BUFFER_SEC = 10


@pytest.mark.acceptance
@pytest.mark.forked
def test_maintenance_transition(monitor_tango_servers, event_store_class, dish_manager_proxy):
    """Test transition to MAINTENANCE."""
    result_event_store = event_store_class()
    progress_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "longrunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    # SetMaintenanceMode triggers a stow request. Taking
    # elevation speed at 1 degree per second, a suitable
    # timeout for the SetMaintenance can be calculated later
    current_el = dish_manager_proxy.achievedPointing[2]
    stow_position = 90.2
    estimate_stow_duration = stow_position - current_el

    [[_], [unique_id]] = dish_manager_proxy.SetMaintenanceMode()
    result_event_store.wait_for_command_id(
        unique_id, timeout=estimate_stow_duration + WAIT_FOR_RESULT_BUFFER_SEC
    )

    expected_progress_updates = [
        "SetMaintenanceMode called on SPF",
        "Stow called on DS",
        "SetStandbyMode called on SPFRX",
        "Awaiting dishmode change to MAINTENANCE",
        "Released authority on DSManager.",
        "SetMaintenanceMode completed",
    ]

    events = progress_event_store.wait_for_progress_update(expected_progress_updates[-1])

    events_string = "".join([str(event) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string

    assert dish_manager_proxy.dishMode == DishMode.MAINTENANCE
