"""Tests dish manager component manager setstandbylp command handler"""

from unittest.mock import MagicMock, patch

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.dish_enums import DishMode


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    MagicMock(return_value=True),
)
@patch("json.dumps", MagicMock(return_value="mocked sub-device-command-ids"))
def test_abort_handler(
    component_manager: DishManagerComponentManager,
    mock_command_tracker: MagicMock,
    callbacks: dict,
) -> None:
    """
    Verify behaviour of Abort command handler.

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
    mock_abort_event = MagicMock()
    mock_abort_event.is_set.return_value = False

    # issue an abort while the command is busy running
    # import ipdb;ipdb.set_trace()
    component_manager.abort(callbacks["task_cb"], mock_abort_event)
    # wait a bit for the lrc updates to come through
    component_state_cb = callbacks["comp_state_cb"]
    component_state_cb.get_queue_values(timeout=60)

    expected_call_kwargs = (
        {"status": TaskStatus.IN_PROGRESS},
        {
            "progress": "SetStandbyLPMode Aborted",
            "status": TaskStatus.ABORTED,
            "result": (ResultCode.ABORTED, "SetStandbyLPMode Aborted"),
        },
        {
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, "Abort sequence completed"),
        },
    )

    # import ipdb;ipdb.set_trace()
    # check that the abort lrc updates come through
    actual_call_kwargs = callbacks["task_cb"].call_args_list
    for count, mock_call in enumerate(actual_call_kwargs):
        _, kwargs = mock_call
        assert kwargs == expected_call_kwargs[count]

    # check that the component state reports the requested command
    component_manager._update_component_state(dishmode=DishMode.STANDBY_FP)
    component_state_cb.wait_for_value("dishmode", DishMode.STANDBY_FP)
