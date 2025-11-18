"""Tests dish manager component manager track command handler."""

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.dish_enums import DishMode, PointingState


@pytest.mark.unit
def test_track_handler(
    component_manager: DishManagerComponentManager,
    callbacks: dict,
) -> None:
    """Verify behaviour of Track command handler.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    component_state_cb = callbacks["comp_state_cb"]
    # track commmand does not use the dish mode model
    # ensure that the preconditions are satisfied before the command is triggered
    component_manager._update_component_state(dishmode=DishMode.OPERATE)
    component_state_cb.wait_for_value("dishmode", DishMode.OPERATE)
    component_manager._update_component_state(pointingstate=PointingState.READY)
    component_state_cb.wait_for_value("pointingstate", PointingState.READY)

    component_manager.track_cmd(callbacks["task_cb"])
    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values()

    expected_call_kwargs = (
        {"status": TaskStatus.QUEUED},
        {"status": TaskStatus.IN_PROGRESS},
        {
            "status": TaskStatus.COMPLETED,
            "result": (
                ResultCode.OK,
                (
                    "Track command has been executed on DS. "
                    "Monitor the achievedTargetLock attribute to determine "
                    "when the dish is on source."
                ),
            ),
        },
    )

    # check that the initial lrc updates come through
    actual_call_kwargs = callbacks["task_cb"].call_args_list
    for count, mock_call in enumerate(actual_call_kwargs):
        _, kwargs = mock_call
        assert kwargs == expected_call_kwargs[count]

    progress_cb = callbacks["progress_cb"]
    expected_progress_updates = [
        "Fanned out commands: DS.Track",
        "DS.Track completed",
        "Track command has been executed on DS. "
        "Monitor the achievedTargetLock attribute to determine when the dish is on source.",
    ]
    progress_updates = progress_cb.get_args_queue()
    for msg in expected_progress_updates:
        assert (msg,) in progress_updates

    # check that the component state reports the requested command
    component_manager._update_component_state(pointingstate=PointingState.TRACK)
    component_state_cb.wait_for_value("pointingstate", PointingState.TRACK)

    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values()
    # check that the final lrc updates come through
    task_cb = callbacks["task_cb"]
    task_cb.assert_called_with(
        progress=(
            "Track command has been executed on DS. "
            "Monitor the achievedTargetLock attribute to determine when the dish is on source."
        ),
        status=TaskStatus.COMPLETED,
        result=(
            ResultCode.OK,
            (
                "Track command has been executed on DS. "
                "Monitor the achievedTargetLock attribute to determine when the dish is on source."
            ),
        ),
    )
