"""Unit tests for Abort/AbortCommands command."""

from unittest.mock import Mock

import pytest
import tango
from ska_control_model import AdminMode, ResultCode, TaskStatus

from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    PointingState,
    SPFOperatingMode,
)
from ska_mid_dish_manager.utils.ska_epoch_to_tai import get_current_tai_timestamp_from_unix_time


@pytest.mark.unit
@pytest.mark.forked
def test_abort_commands_raises_deprecation_warning(dish_manager_resources):
    # this test will be removed when AbortCommands is also removed
    device_proxy, _ = dish_manager_resources
    with pytest.warns(DeprecationWarning) as record:
        device_proxy.AbortCommands()

    # check that only one warning was raised
    assert len(record) == 1
    # check that the message matches
    warning_msg = (
        "AbortCommands is deprecated, use Abort instead. "
        "Issuing Abort sequence for requested command."
    )
    assert record[0].message.args[0] == warning_msg


@pytest.mark.unit
@pytest.mark.forked
def test_only_one_abort_runs_at_a_time(dish_manager_resources):
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    # update the execute_command mock to return IN_PROGRESS and a timestamp
    ds_cm.execute_command = Mock(return_value=(TaskStatus.IN_PROGRESS, 1234567890.0))

    [[result_code], [_]] = device_proxy.Abort()
    assert result_code == ResultCode.STARTED

    # check that second abort trigger is rejected
    [[result_code], [_]] = device_proxy.Abort()
    assert result_code == ResultCode.REJECTED


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "abort_cmd",
    [
        ("Abort"),
        ("AbortCommands"),
    ],
)
def test_abort_is_rejected_in_maintenance_dishmode(
    abort_cmd, dish_manager_resources, event_store_class
):
    """Verify Abort/AbortCommands is rejected when DishMode is MAINTENANCE."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]
    spfrx_cm = dish_manager_cm.sub_component_managers["SPFRX"]

    dish_mode_event_store = event_store_class()

    device_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )

    ds_cm._update_component_state(operatingmode=DSOperatingMode.STOW)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.MAINTENANCE)
    spfrx_cm._update_component_state(adminmode=AdminMode.ENGINEERING)

    dish_mode_event_store.wait_for_value(DishMode.MAINTENANCE)
    assert device_proxy.dishMode == DishMode.MAINTENANCE

    [[result_code], [_]] = device_proxy.command_inout(abort_cmd, None)
    assert result_code == ResultCode.REJECTED


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "abort_cmd, pointing_state",
    [
        ("Abort", PointingState.SLEW),
        ("AbortCommands", PointingState.TRACK),
    ],
)
def test_abort_during_dish_movement(
    dish_manager_resources, event_store_class, abort_cmd, pointing_state
):
    """Verify Abort/AbortCommands executes the abort sequence."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]

    # update the execute_command mock to return IN_PROGRESS and a timestamp
    ds_cm.execute_command = Mock(return_value=(TaskStatus.IN_PROGRESS, 1234567890.0))

    dish_mode_event_store = event_store_class()
    progress_event_store = event_store_class()
    result_event_store = event_store_class()
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
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )

    device_proxy.subscribe_event(
        "longRunningCommandsInQueue",
        tango.EventType.CHANGE_EVENT,
        cmds_in_queue_store,
    )
    # since we check that the queue is empty, remove the empty queue
    # event received after subscription to prevent false reporting
    cmds_in_queue_store.clear_queue()

    # tracktable will be reset when the dish is tracking. this will make another call to
    # DS to fetch a tai calculation. just replace that object to use the manual approach
    if pointing_state == PointingState.TRACK:
        dish_manager_cm.get_current_tai_offset_from_dsc_with_manual_fallback = (
            get_current_tai_timestamp_from_unix_time
        )
        # mock the reply from ds to load a track table (happens during the table reset)
        mock_response = Mock()
        mock_response.return_value = ResultCode.OK, ""
        dish_manager_cm.track_load_table = mock_response

    [[_], [fp_unique_id]] = device_proxy.SetStandbyFPMode()
    # dont update spf operatingMode to mimic skipAttributeUpdate=True
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_FP)
    # we can now expect dishMode to transition to UNKNOWN
    dish_mode_event_store.wait_for_value(DishMode.UNKNOWN, timeout=30)
    assert device_proxy.dishMode == DishMode.UNKNOWN
    # remove the progress events emitted from SetStandbyFPMode execution
    progress_event_store.clear_queue()

    # update the pointingState to simulate a dish movement
    ds_cm._update_component_state(pointingstate=pointing_state)

    # Abort the LRC
    [[_], [abort_unique_id]] = device_proxy.command_inout(abort_cmd, None)
    result_event_store.wait_for_command_id(fp_unique_id, timeout=30)
    progress_event_store.wait_for_progress_update("SetStandbyFPMode Aborted")

    expected_progress_updates = [
        "Clearing scanID",
        "EndScan completed",
        "Fanned out commands: SPF.SetOperateMode, DS.SetStandbyFPMode",
        "Awaiting dishmode change to STANDBY_FP",
    ]

    if pointing_state == PointingState.SLEW:
        slew_progress_updates = [
            "Fanned out commands: DS.TrackStop",
            "Awaiting pointingstate change to READY",
            "DS pointingstate changed to READY",
            "TrackStop completed",
        ]
        expected_progress_updates = slew_progress_updates + expected_progress_updates

    ds_cm._update_component_state(pointingstate=PointingState.READY)
    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=30
    )
    events_string = "".join([str(event.attr_value.value) for event in events])
    for message in expected_progress_updates:
        assert message in events_string

    # trigger update on spf to make sure FP transition happens
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    progress_event_store.wait_for_progress_update("SetStandbyFPMode completed", timeout=30)

    # Confirm that abort finished and the queue is cleared
    result_event_store.wait_for_command_id(abort_unique_id)
    cmds_in_queue_store.wait_for_value((), timeout=30)
    assert device_proxy.dishMode == DishMode.STANDBY_FP
