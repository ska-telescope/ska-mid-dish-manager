"""Tests dish manager component manager trackloadstaticoff command handler."""

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager


@pytest.mark.unit
def test_track_load_static_off_handler(
    component_manager: DishManagerComponentManager,
    callbacks: dict,
) -> None:
    """Verify behaviour of TrackLoadStaticOff command handler.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    # slew has no pre-condition
    component_manager.track_load_static_off(
        [
            1.0,
            2.0,
        ],
        callbacks["task_cb"],
    )
    # wait a bit for the lrc updates to come through
    component_state_cb = callbacks["comp_state_cb"]
    component_state_cb.get_queue_values()

    expected_call_kwargs = (
        {"status": TaskStatus.QUEUED},
        {"status": TaskStatus.IN_PROGRESS},
        {
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, "TrackLoadStaticOff completed"),
        },
    )

    # check that the initial lrc updates come through
    actual_call_kwargs = callbacks["task_cb"].call_args_list
    for count, mock_call in enumerate(actual_call_kwargs):
        _, kwargs = mock_call
        assert kwargs == expected_call_kwargs[count]

    progress_cb = callbacks["progress_cb"]
    progress_cb.wait_for_args(
        ("Awaiting DS actstaticoffsetvaluexel, actstaticoffsetvalueel change to 1.0, 2.0",)
    )
    progress_cb.wait_for_args(("Fanned out commands: DS.TrackLoadStaticOff",))
    progress_cb.wait_for_args(
        ("Awaiting actstaticoffsetvaluexel, actstaticoffsetvalueel change to 1.0, 2.0",)
    )
    progress_cb.wait_for_args(("TrackLoadStaticOff completed",))
