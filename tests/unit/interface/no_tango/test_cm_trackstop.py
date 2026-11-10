"""Tests dish manager component manager trackstop command handler."""

import threading
from unittest.mock import MagicMock, call

import pytest
from ska_control_model import TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.dish_enums import PointingState


@pytest.mark.unit
def test_track_stop_handler(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
    task_abort_event: threading.Event,
) -> None:
    """Verify behaviour of TrackStop command handler.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks
    :param task_abort_event: threading event to signal task abortion
    """
    component_state_cb = callbacks["comp_state_cb"]
    task_cb = callbacks["task_cb"]

    threading.Thread(
        target=component_manager.track_stop_cmd,
        args=(),
        kwargs={"task_callback": task_cb, "task_abort_event": task_abort_event},
        daemon=True,
    ).start()
    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values(timeout=1)

    component_manager.sub_component_managers["DS"]._update_component_state(
        pointingstate=PointingState.READY
    )
    component_manager._update_component_state(pointingstate=PointingState.READY)
    component_state_cb.wait_for_value("pointingstate", PointingState.READY)

    # check that the updates come through
    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=None, progress_info="Awaiting DS pointingstate change to READY"),
        call(progress=None, progress_info="Fanned out commands: DS.TrackStop"),
        call(progress=None, progress_info="Awaiting pointingstate change to READY"),
        # call(status=TaskStatus.COMPLETED, result=(ResultCode.OK, "TrackStop completed.")),
    ]
