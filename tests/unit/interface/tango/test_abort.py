"""Unit tests for Abort/AbortCommands command."""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
)


@pytest.mark.unit
@pytest.mark.forked
def test_abort_lrc(dish_manager_resources, event_store_class):
    """Verify AbortCommands cancels a lrc."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]

    dish_mode_event_store = event_store_class()
    progress_event_store = event_store_class()
    cmds_in_queue_store = event_store_class()

    device_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )

    device_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    device_proxy.subscribe_event(
        "longRunningCommandsInQueue",
        tango.EventType.CHANGE_EVENT,
        cmds_in_queue_store,
    )
    # since we check that the queue is empty, remove the empty queue
    # event received after subscription to prevent false reporting
    cmds_in_queue_store.clear_queue()

    device_proxy.SetStandbyFPMode()
    # dont update spf operatingMode to mimic skipAttributeUpdate=True
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_FP)
    # we can now expect dishMode to transition to UNKNOWN
    dish_mode_event_store.wait_for_value(DishMode.UNKNOWN, timeout=30)
    assert device_proxy.dishMode == DishMode.UNKNOWN
    # remove the progress events emitted from SetStandbyFPMode execution
    progress_event_store.clear_queue()

    # Abort the LRC
    device_proxy.AbortCommands()
    progress_event_store.wait_for_progress_update("SetStandbyFPMode Aborted")

    # Confirm that abort finished and the queue is cleared
    cmds_in_queue_store.wait_for_value((), timeout=30)
