"""Tests dish manager component manager trackstop command handler."""

import pytest
from ska_control_model import ResultCode, TaskStatus
from ska_mid_dish_ds_manager.models.dish_enums import (
    PointingState,
)
from ska_mid_dish_utils.models.dish_enums import DishMode

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager


@pytest.mark.unit
def test_track_stop_handler(
    component_manager: DishManagerComponentManager,
    callbacks: dict,
) -> None:
    """Verify behaviour of TrackStop command handler.

    :param component_manager: the component manager under test
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
    )

    # check that the initial lrc updates come through
    actual_call_kwargs = callbacks["task_cb"].call_args_list
    for count, mock_call in enumerate(actual_call_kwargs):
        _, kwargs = mock_call
        assert kwargs == expected_call_kwargs[count]

    progress_cb = callbacks["progress_cb"]
    expected_progress_updates = [
        "Awaiting DS pointingstate change to READY",
        "Fanned out commands: DS.TrackStop",
        "Awaiting pointingstate change to READY",
    ]
    progress_updates = progress_cb.get_args_queue()
    for msg in expected_progress_updates:
        assert (msg,) in progress_updates

    # check that the component state reports the requested command
    component_manager.sub_component_managers["DS"]._update_component_state(
        pointingstate=PointingState.READY
    )
    component_manager._update_component_state(pointingstate=PointingState.READY)
    component_state_cb.wait_for_value("pointingstate", PointingState.READY)

    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values()
    # check that the final lrc updates come through
    task_cb = callbacks["task_cb"]
    task_cb.assert_called_with(
        status=TaskStatus.COMPLETED,
        result=(ResultCode.OK, "TrackStop completed"),
    )
    progress_cb.wait_for_args(("TrackStop completed",))
