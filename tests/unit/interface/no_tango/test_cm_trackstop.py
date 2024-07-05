"""Tests dish manager component manager trackstop command handler"""

from unittest.mock import Mock, patch

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.dish_enums import DishMode, PointingState


@pytest.mark.unit
@patch("json.dumps", Mock(return_value="mocked sub-device-command-ids"))
def test_track_stop_handler(
    component_manager: DishManagerComponentManager,
    mock_command_tracker: Mock,
    callbacks: dict,
) -> None:
    """
    Verify behaviour of TrackStop command handler.

    :param component_manager: the component manager under test
    :param mock_command_tracker: a representing the command tracker class
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    component_state_cb = callbacks["comp_state_cb"]
    # trackstop commmand does not use the dish mode model
    # ensure that its precondition is satisfied before command trigger
    desired_state = {"dishmode": DishMode.OPERATE, "pointingstate": PointingState.TRACK}
    component_manager._update_component_state(**desired_state)
    component_state = component_state_cb.get_queue_values()
    assert desired_state in component_state

    component_manager.track_stop_cmd(callbacks["task_cb"])
    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values()

    expected_call_kwargs = (
        {"status": TaskStatus.QUEUED},
        {"status": TaskStatus.IN_PROGRESS},
        {"progress": f"TrackStop called on DS, ID {mock_command_tracker.new_command()}"},
        {"progress": "Awaiting DS pointingstate change to [<PointingState.READY: 0>]"},
        {"progress": "Commands: mocked sub-device-command-ids"},
        {"progress": "Awaiting pointingstate change to READY"},
    )

    # check that the initial lrc updates come through
    actual_call_kwargs = callbacks["task_cb"].call_args_list
    for count, mock_call in enumerate(actual_call_kwargs):
        _, kwargs = mock_call
        assert kwargs == expected_call_kwargs[count]

    # check that the component state reports the requested command
    component_manager._update_component_state(pointingstate=PointingState.READY)
    component_state_cb.wait_for_value("pointingstate", PointingState.READY)

    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values()
    # check that the final lrc updates come through
    task_cb = callbacks["task_cb"]
    task_cb.assert_called_with(
        progress="TrackStop completed",
        status=TaskStatus.COMPLETED,
        result=(ResultCode.OK, "TrackStop completed"),
    )
