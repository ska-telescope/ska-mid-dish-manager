"""Tests dish manager component manager trackloadstaticoff command handler"""

from unittest.mock import Mock, patch

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager


@pytest.mark.unit
@patch("json.dumps", Mock(return_value="mocked sub-device-command-ids"))
def test_track_load_static_off_handler(
    component_manager: DishManagerComponentManager,
    mock_command_tracker: Mock,
    callbacks: dict,
) -> None:
    """
    Verify behaviour of TrackLoadStaticOff command handler.

    :param component_manager: the component manager under test
    :param mock_command_tracker: a representing the command tracker class
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
        {"progress": f"TrackLoadStaticOff called on DS, ID {mock_command_tracker.new_command()}"},
        {
            "progress": "Awaiting DS actstaticoffsetvaluexel, actstaticoffsetvalueel change to "
            "1.0, 2.0"
        },
        {"progress": "Commands: mocked sub-device-command-ids"},
        {
            "progress": "Awaiting actstaticoffsetvaluexel, actstaticoffsetvalueel change to "
            "1.0, 2.0"
        },
        {
            "progress": "TrackLoadStaticOff completed",
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, "TrackLoadStaticOff completed"),
        },
    )

    # check that the initial lrc updates come through
    actual_call_kwargs = callbacks["task_cb"].call_args_list
    print(actual_call_kwargs)
    for count, mock_call in enumerate(actual_call_kwargs):
        _, kwargs = mock_call
        assert kwargs == expected_call_kwargs[count]
