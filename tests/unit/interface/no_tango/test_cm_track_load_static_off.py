"""Tests dish manager component manager trackloadstaticoff command handler."""

import threading
from unittest.mock import MagicMock, call

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager


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
    component_state_cb = callbacks["comp_state_cb"]
    task_cb = callbacks["task_cb"]

    threading.Thread(
        target=component_manager.track_load_static_off,
        args=([1.0, 2.0],),
        kwargs={"task_callback": task_cb, "task_abort_event": task_abort_event},
        daemon=True,
    ).start()
    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values(timeout=1)

    component_manager.sub_component_managers["DS"]._update_component_state(
        **{"actstaticoffsetvaluexel": 1.0, "actstaticoffsetvalueel": 2.0}
    )

    # check that the updates come through
    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        call(
            progress=None,
            progress_info=(
                "Awaiting DS actstaticoffsetvaluexel, actstaticoffsetvalueel change to 1.0, 2.0"
            ),
        ),
        call(progress=None, progress_info="Fanned out commands: DS.TrackLoadStaticOff"),
        call(
            progress=None,
            progress_info=(
                "Awaiting actstaticoffsetvaluexel, actstaticoffsetvalueel change to 1.0, 2.0"
            ),
        ),
        # call(status=TaskStatus.COMPLETED,
        #      result=(ResultCode.OK, "TrackLoadStaticOff completed.")),
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
