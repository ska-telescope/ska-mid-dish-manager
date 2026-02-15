"""Unit tests verifying model against DS_SetStowMode transition."""

import pytest
import tango
from ska_mid_dish_utils.models.dish_enums import (
    DSOperatingMode,
)


@pytest.mark.unit
@pytest.mark.forked
def test_stow_mode(dish_manager_resources, event_store_class):
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]

    result_event_store = event_store_class()
    status_event_store = event_store_class()

    device_proxy.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )

    device_proxy.subscribe_event(
        "Status",
        tango.EventType.CHANGE_EVENT,
        status_event_store,
    )

    device_proxy.SetStowMode()
    # wait a bit before forcing the updates on the subcomponents
    result_event_store.get_queue_values()
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STOW)

    expected_progress_update = "Stow called, monitor dishmode for LRC completed"
    status_event_store.wait_for_progress_update(expected_progress_update, timeout=6)
