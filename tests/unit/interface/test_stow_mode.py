"""Unit tests verifying model against DS_SetStowMode transition."""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DSOperatingMode


# pylint: disable=missing-function-docstring, protected-access
@pytest.mark.unit
@pytest.mark.forked
def test_stow_mode(dish_manager_resources, event_store_class):
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]

    progress_event_store = event_store_class()
    result_event_store = event_store_class()

    device_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    device_proxy.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )

    device_proxy.SetStowMode()
    # wait a bit before forcing the updates on the subcomponents
    result_event_store.get_queue_values()
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STOW)

    expected_progress_updates = [
        "Stow called on DS",
        "Awaiting dishMode change to STOW",
        "Stow completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )
    events_string = "".join([str(event.attr_value.value) for event in events])
    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string
