"""Tests dish manager component manager slew command handler."""

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.dish_enums import DishMode, PointingState


@pytest.mark.unit
def test_slew_handler(
    component_manager: DishManagerComponentManager,
    callbacks: dict,
) -> None:
    """Verify behaviour of Slew command handler.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    # slew has a pre-condition: dishMode to be in operate and pointing state is ready
    component_state_cb = callbacks["comp_state_cb"]
    component_manager._update_component_state(dishmode=DishMode.OPERATE)
    component_state_cb.wait_for_value("dishmode", DishMode.OPERATE)
    component_manager._update_component_state(pointingstate=PointingState.READY)
    component_state_cb.wait_for_value("pointingstate", PointingState.READY)

    component_manager.slew([20.0, 30.0], callbacks["task_cb"])
    # wait a bit for the lrc updates to come through
    component_state_cb = callbacks["comp_state_cb"]
    component_state_cb.get_queue_values(timeout=1)

    expected_call_kwargs = (
        {"status": TaskStatus.QUEUED},
        {"status": TaskStatus.IN_PROGRESS},
        {
            "status": TaskStatus.COMPLETED,
            "result": (
                ResultCode.OK,
                "The DS has been commanded to Slew to [20.0, 30.0]. Monitor the pointing"
                " attributes for the completion status of the task.",
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
        "Fanned out commands: DS.Slew",
        "DS.Slew completed",
        "The DS has been commanded to Slew to [20.0, 30.0]. "
        "Monitor the pointing attributes for the completion status of the task.",
    ]
    progress_updates = progress_cb.get_args_queue()
    for msg in expected_progress_updates:
        assert (msg,) in progress_updates

    # check that the component state reports the requested command
    component_manager._update_component_state(pointingstate=PointingState.SLEW)
    component_manager.sub_component_managers["DS"]._update_component_state(
        pointingstate=PointingState.SLEW
    )
    component_state_cb.wait_for_value("pointingstate", PointingState.SLEW)
