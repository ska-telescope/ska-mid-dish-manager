"""Tests dish manager component manager track command handler."""

import threading
from unittest.mock import MagicMock, call

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.dish_enums import PointingState
from tests.utils import progress_call


@pytest.mark.unit
def test_track_handler(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
    task_abort_event: threading.Event,
) -> None:
    """Verify behaviour of Track command handler.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks
    :param task_abort_event: threading event to signal task abortion
    """
    component_state_cb = callbacks["comp_state_cb"]
    task_cb = callbacks["task_cb"]
    ds_cm = component_manager.sub_component_managers["DS"]

    command_thread = threading.Thread(
        target=component_manager.track_cmd,
        args=(),
        kwargs={"task_callback": task_cb, "task_abort_event": task_abort_event},
        daemon=True,
    )
    command_thread.start()

    ds_cm._update_component_state(pointingstate=PointingState.TRACK)
    # check that the component state reports the requested command
    component_state_cb.wait_for_value("pointingstate", PointingState.TRACK)

    # wait for all the updates to be processed by the command thread
    command_thread.join(timeout=30)
    assert not command_thread.is_alive(), "Track did not finish in time"
    # check that the updates come through
    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        progress_call("Track started"),
        progress_call("DS.Track started"),
        progress_call("Fanned out commands: DS.Track"),
        progress_call("DS.Track completed"),
        progress_call(
            "Track command has been executed on DS. "
            "Monitor the achievedTargetLock attribute to determine when the dish is on source."
        ),
        call(
            status=TaskStatus.COMPLETED,
            result=(
                ResultCode.OK,
                "Track command has been executed on DS. "
                "Monitor the achievedTargetLock attribute to determine "
                "when the dish is on source.",
            ),
        ),
    ]
