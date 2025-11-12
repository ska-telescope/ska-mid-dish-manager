"""Unit tests verifying model against DS_SetStowMode transition."""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DSOperatingMode
from ska_mid_dish_manager.utils.method_calls_store_helper import MethodCallsStore


@pytest.mark.unit
@pytest.mark.forked
def test_stow_mode(dish_manager_resources, event_store_class):
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]

    result_event_store = event_store_class()

    command_progress_callback = MethodCallsStore()
    dish_manager_cm._command_progress_callback = command_progress_callback

    device_proxy.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )

    device_proxy.SetStowMode()
    # wait a bit before forcing the updates on the subcomponents
    result_event_store.get_queue_values()
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STOW)

    expected_progress_update = ("Stow called, monitor dishmode for LRC completed",)
    command_progress_callback.wait_for_args(expected_progress_update, timeout=30)
