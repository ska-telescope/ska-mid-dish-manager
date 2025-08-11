"""Test Maintenance Mode."""

import pytest

from ska_mid_dish_manager.models.constants import (
    STOW_ELEVATION_DEGREES,
    STOW_SPEED_DEGREES_PER_SECOND,
)
from ska_mid_dish_manager.models.dish_enums import DishMode
from tests.utils import remove_subscriptions, setup_subscriptions

WAIT_FOR_RESULT_BUFFER_SEC = 10


@pytest.mark.acceptance
@pytest.mark.forked
def test_maintenance_transition(monitor_tango_servers, event_store_class, dish_manager_proxy):
    """Test transition to MAINTENANCE."""
    result_event_store = event_store_class()
    progress_event_store = event_store_class()
    attr_cb_mapping = {
        "longRunningCommandProgress": progress_event_store,
        "longRunningCommandResult": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    current_el = dish_manager_proxy.achievedPointing[2]
    estimated_stow_duration = (
        abs(STOW_ELEVATION_DEGREES - current_el) / STOW_SPEED_DEGREES_PER_SECOND
    )

    [[_], [unique_id]] = dish_manager_proxy.SetMaintenanceMode()
    result_event_store.wait_for_command_id(
        unique_id, timeout=estimated_stow_duration + WAIT_FOR_RESULT_BUFFER_SEC
    )

    expected_progress_updates = [
        "Stow called on DS",
        "Awaiting DS operatingmode change to STOW",
        "SetStandbyMode called on SPFRX",
        "Awaiting SPFRX operatingmode change to STANDBY",
        "SetMaintenanceMode called on SPF",
        "Awaiting SPF operatingmode change to MAINTENANCE",
        "Awaiting dishmode change to MAINTENANCE",
        "SetMaintenanceMode [1/2] completed",
        "ReleaseAuth called on DS",
        "Awaiting DS dsccmdauth change to NO_AUTHORITY",
        "SetMaintenanceMode [2/2] completed",
    ]

    events = progress_event_store.wait_for_progress_update(expected_progress_updates[-1])

    events_string = "".join([str(event.attr_value.value) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string

    assert dish_manager_proxy.dishMode == DishMode.MAINTENANCE

    remove_subscriptions(subscriptions)
