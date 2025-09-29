"""Tests dish manager component manager abort command handler."""

from unittest.mock import MagicMock, patch

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    MagicMock(return_value=True),
)
def test_abort_handler(
    component_manager: DishManagerComponentManager,
    mock_command_tracker: MagicMock,
    callbacks: dict,
) -> None:
    """Verify behaviour of Abort command handler.

    :param component_manager: the component manager under test
    :param mock_command_tracker: a representing the command tracker class
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
    task_status, message = component_manager.abort_commands()
    assert task_status == TaskStatus.IN_PROGRESS
    assert message == "Aborting tasks"

    # wait a bit for the lrc updates to come through
    component_state_cb = callbacks["comp_state_cb"]
    component_state_cb.get_queue_values(timeout=60)

    expected_call_kwargs = (
        {
            "progress": "SetStandbyLPMode Aborted",
            "status": TaskStatus.ABORTED,
            "result": (ResultCode.ABORTED, "SetStandbyLPMode Aborted"),
        },
    )

    # check that the abort lrc updates come through
    actual_call_kwargs = callbacks["task_cb"].call_args_list
    for count, mock_call in enumerate(actual_call_kwargs):
        _, kwargs = mock_call
        assert kwargs == expected_call_kwargs[count]
