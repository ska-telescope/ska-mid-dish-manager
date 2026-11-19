"""Tests dish manager component manager trackloadstaticoff command handler."""

import threading
from unittest.mock import MagicMock, call

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from tests.utils import progress_call


@pytest.mark.unit
def test_track_load_static_off_handler(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
    task_abort_event: threading.Event,
) -> None:
    """Verify behaviour of TrackLoadStaticOff command handler.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks
    :param task_abort_event: threading event to signal task abortion
    """
    task_cb = callbacks["task_cb"]
    ds_cm = component_manager.sub_component_managers["DS"]

    command_thread = threading.Thread(
        target=component_manager.track_load_static_off,
        args=([1.0, 2.0],),
        kwargs={"task_callback": task_cb, "task_abort_event": task_abort_event},
        daemon=True,
    )
    command_thread.start()

    ds_cm._update_component_state(
        **{"actstaticoffsetvaluexel": 1.0, "actstaticoffsetvalueel": 2.0}
    )

    # wait for all the updates to be processed by the command thread
    command_thread.join(timeout=30)
    assert not command_thread.is_alive(), "TrackLoadStaticOff did not finish in time"
    # check that the updates come through
    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        progress_call("TrackLoadStaticOff started"),
        progress_call("DS.TrackLoadStaticOff started"),
        progress_call(
            "Awaiting DS actstaticoffsetvaluexel, actstaticoffsetvalueel change to 1.0, 2.0"
        ),
        progress_call("Fanned out commands: DS.TrackLoadStaticOff"),
        progress_call(
            "Awaiting actstaticoffsetvaluexel, actstaticoffsetvalueel change to 1.0, 2.0"
        ),
        progress_call("DS actstaticoffsetvaluexel changed to 1.0"),
        progress_call("DS actstaticoffsetvalueel changed to 2.0"),
        progress_call("DS.TrackLoadStaticOff completed"),
        progress_call("TrackLoadStaticOff completed."),
        call(status=TaskStatus.COMPLETED, result=(ResultCode.OK, "TrackLoadStaticOff completed.")),
    ]


@pytest.mark.unit
@pytest.mark.parametrize(
    "values, args_len",
    [([], 0), ([1.0], 1), ([1.0, 2.0, 3.0], 3), ([1.0, 2.0, 3.0, 4.0], 4)],
)
def test_track_load_static_off_rejects_invalid_args_count(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
    values: list[float],
    args_len: int,
    task_abort_event: threading.Event,
) -> None:
    """Verify invalid argument counts are rejected."""
    task_cb = callbacks["task_cb"]
    component_manager.track_load_static_off(
        values, task_callback=task_cb, task_abort_event=task_abort_event
    )

    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        call(
            status=TaskStatus.COMPLETED,
            result=(
                ResultCode.REJECTED,
                f"Expected 2 arguments (off_xel, off_el) but got {args_len} arg(s).",
            ),
        ),
    ]
