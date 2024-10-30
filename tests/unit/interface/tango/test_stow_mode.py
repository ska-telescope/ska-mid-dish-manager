"""Unit tests verifying model against DS_SetStowMode transition."""

import pytest
import tango
from ska_control_model import ResultCode

from ska_mid_dish_manager.models.dish_enums import DSOperatingMode


# pylint: disable=missing-function-docstring, protected-access
@pytest.mark.unit
@pytest.mark.forked
def test_stow_mode(dish_manager_resources, event_store_class):
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]

    progress_event_store = event_store_class()
    result_event_store = event_store_class()
    lrc_status_event_store = event_store_class()

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

    device_proxy.subscribe_event(
        "longRunningCommandStatus",
        tango.EventType.CHANGE_EVENT,
        lrc_status_event_store,
    )

    ds_cm._update_component_state(operatingmode=DSOperatingMode.POINT)

    [[result_code], [unique_id]] = device_proxy.SetStowMode()
    assert result_code == ResultCode.STARTED

    expected_progress_update = "Stow called"
    progress_event_store.wait_for_progress_update(expected_progress_update, timeout=6)

    ds_cm._update_component_state(operatingmode=DSOperatingMode.STOW)

    expected_progress_update = "Stow completed"
    progress_event_store.wait_for_progress_update(expected_progress_update, timeout=6)

    result_event_store.wait_for_command_result(unique_id, '[0, "Stow completed"]')

    lrc_status_event_store.wait_for_value(
        (
            unique_id,
            "COMPLETED",
        )
    )


# pylint: disable=missing-function-docstring, protected-access
@pytest.mark.unit
@pytest.mark.forked
def test_only_one_stow_runs_at_a_time(dish_manager_resources, event_store_class):
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]

    ds_cm._update_component_state(operatingmode=DSOperatingMode.POINT)

    [[result_code], [_]] = device_proxy.SetStowMode()
    assert result_code == ResultCode.STARTED

    [[result_code], [_]] = device_proxy.SetStowMode()
    assert result_code == ResultCode.REJECTED
