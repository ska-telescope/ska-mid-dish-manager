"""Tests dish manager component manager slew command handler."""

import threading
from unittest.mock import MagicMock, call

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.dish_enums import PointingState
from tests.utils import progress_call


@pytest.mark.unit
def test_slew_handler(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
    task_abort_event: threading.Event,
) -> None:
    """Verify behaviour of Slew command handler.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks
    :param task_abort_event: threading event to signal task abortion
    """
    component_state_cb = callbacks["comp_state_cb"]
    task_cb = callbacks["task_cb"]
    ds_cm = component_manager.sub_component_managers["DS"]

    command_thread = threading.Thread(
        target=component_manager.slew,
        args=([20.0, 30.0],),
        kwargs={"task_callback": task_cb, "task_abort_event": task_abort_event},
        daemon=True,
    )
    command_thread.start()

    # check that the component state reports the requested command
    # component_manager._update_component_state(pointingstate=PointingState.SLEW)
    ds_cm._update_component_state(pointingstate=PointingState.SLEW)
    component_state_cb.wait_for_value("pointingstate", PointingState.SLEW)

    # wait for all the updates to be processed by the command thread
    command_thread.join(timeout=30)
    assert not command_thread.is_alive(), "SetStandbyLPMode did not finish in time"
    # check that the updates come through
    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        progress_call("Slew started"),
        progress_call("DS.Slew started"),
        progress_call("Fanned out commands: DS.Slew"),
        progress_call("DS.Slew completed"),
        progress_call(
            "The DS has been commanded to Slew to [20.0, 30.0]. "
            "Monitor the pointing attributes for the completion status of the task."
        ),
        call(
            status=TaskStatus.COMPLETED,
            result=(
                ResultCode.OK,
                "The DS has been commanded to Slew to [20.0, 30.0]. "
                "Monitor the pointing attributes for the completion status of the task.",
            ),
        ),
    ]


@pytest.mark.unit
@pytest.mark.parametrize(
    "invalid_slew_args, args_len",
    [
        ([], 0),
        ([100], 1),
        ([100, 100, 100], 3),
        ([100, 100, 100, 100], 4),
        ([100, 100, 100, 100, 100], 5),
        ([100, 100, 100, 100, 100, 100], 6),
    ],
)
def test_slew_rejection(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
    invalid_slew_args,
    args_len: int,
    task_abort_event: threading.Event,
) -> None:
    """Verify behaviour of a Slew rejection given too many arguments."""
    task_cb = callbacks["task_cb"]
    component_manager.slew(
        invalid_slew_args, task_callback=task_cb, task_abort_event=task_abort_event
    )

    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        call(
            status=TaskStatus.COMPLETED,
            result=(
                ResultCode.REJECTED,
                f"Expected 2 arguments (az, el) but got {args_len} arg(s).",
            ),
        ),
    ]
