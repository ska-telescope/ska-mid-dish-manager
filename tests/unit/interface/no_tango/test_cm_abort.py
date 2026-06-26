"""Tests dish manager component manager abort/abort_commands command handler."""

from unittest.mock import MagicMock, patch

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.dish_enums import DishMode


@pytest.mark.unit
@pytest.mark.parametrize("abort_method", ["abort", "abort_commands"])
@patch(
    "ska_mid_dish_manager.models.abort_sequence_command_handler.AbortSequenceCommandHandler.execute_abort_sequence",
)
@patch(
    "ska_mid_dish_manager.component_managers.dish_manager_cm.DishManagerComponentManager.abort_tasks",
)
def test_abort_handler_runs_only_one_sequence_at_a_time(
    mock_abort_tasks: MagicMock,
    mock_execute_abort_sequence: MagicMock,
    abort_method: str,
    component_manager: DishManagerComponentManager,
    mock_command_tracker: MagicMock,
) -> None:
    """Verify only one Abort sequence can be requested at a time.

    :param component_manager: the component manager under test
    :param mock_command_tracker: a representing the command tracker class
    :param abort_method: the abort method to test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    abort_func = getattr(component_manager, abort_method)
    task_status, message = abort_func()
    assert task_status == TaskStatus.IN_PROGRESS
    assert message == "Abort sequence has started"
    mock_command_tracker.command_statuses = [("Abort", TaskStatus.IN_PROGRESS)]

    # issue a 2nd abort while the previous is busy running
    task_status, message = abort_func()
    assert task_status == TaskStatus.REJECTED
    assert message == "Existing Abort sequence ongoing"

    assert mock_abort_tasks.call_count == 1
    assert mock_execute_abort_sequence.call_count == 1


@pytest.mark.unit
@pytest.mark.parametrize("abort_method", ["abort", "abort_commands"])
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    MagicMock(return_value=True),
)
@patch(
    "ska_mid_dish_manager.models.abort_sequence_command_handler.AbortSequenceCommandHandler.execute_abort_sequence",
)
def test_abort_handler(
    mock_execute_abort_sequence: MagicMock,
    abort_method: str,
    component_manager: DishManagerComponentManager,
    mock_command_tracker: MagicMock,
    callbacks: dict,
) -> None:
    """Verify behaviour of Abort command handler.

    :param component_manager: the component manager under test
    :param mock_command_tracker: a representing the command tracker class
    :param abort_method: the abort method to test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    component_manager.set_standby_lp_mode(callbacks["task_cb"])

    # wait a bit for the lrc updates to come through
    component_state_cb = callbacks["comp_state_cb"]
    component_state_cb.get_queue_values()
    # clear the initial lrc updates which come through
    callbacks["task_cb"].call_args_list.clear()

    mock_command_tracker.command_statuses = [("SetStandbyLPMode", TaskStatus.IN_PROGRESS)]

    # issue an abort while the command is busy running
    abort_func = getattr(component_manager, abort_method)
    task_status, message = abort_func(callbacks["task_cb"])
    assert task_status == TaskStatus.IN_PROGRESS
    assert message == "Abort sequence has started"

    # wait a bit for the lrc updates to come through
    component_state_cb = callbacks["comp_state_cb"]
    component_state_cb.get_queue_values()

    expected_call_kwargs = (
        {
            "status": TaskStatus.ABORTED,
            "result": (ResultCode.ABORTED, "SetStandbyLPMode aborted"),
        },
    )

    # check that the abort lrc updates come through
    actual_call_kwargs = callbacks["task_cb"].call_args_list
    for count, mock_call in enumerate(actual_call_kwargs):
        _, kwargs = mock_call
        assert kwargs == expected_call_kwargs[count]

    progress_cb = callbacks["progress_cb"]
    progress_cb.wait_for_args(("SetStandbyLPMode aborted",))

    # check that the component state reports the requested command
    component_manager._update_component_state(dishmode=DishMode.STANDBY_FP)
    component_state_cb.wait_for_value("dishmode", DishMode.STANDBY_FP)
