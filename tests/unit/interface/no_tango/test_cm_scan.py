"""Tests dish manager component manager scan command handler"""

from unittest.mock import Mock, patch

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager


@pytest.mark.unit
@patch("json.dumps", Mock(return_value="mocked sub-device-command-ids"))
def test_scan_handler(
    component_manager: DishManagerComponentManager,
    callbacks: dict,
) -> None:
    """
    Verify behaviour of Scan command handler.

    :param component_manager: the component manager under test
    :param mock_command_tracker: a representing the command tracker class
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    # endscan has no pre-condition
    component_manager.scan("scan-id", callbacks["task_cb"])
    # wait a bit for the lrc updates to come through
    component_state_cb = callbacks["comp_state_cb"]
    component_state_cb.get_queue_values()

    expected_call_kwargs = (
        {"status": TaskStatus.QUEUED},
        {
            "progress": "Setting scanID",
            "status": TaskStatus.IN_PROGRESS,
        },
        {
            "progress": "Scan completed",
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, "Scan completed"),
        },
    )

    # check that the initial lrc updates come through
    actual_call_kwargs = callbacks["task_cb"].call_args_list
    for count, mock_call in enumerate(actual_call_kwargs):
        _, kwargs = mock_call
        assert kwargs == expected_call_kwargs[count]

    # check that the scan id is cleared
    assert component_manager.component_state["scanid"] == "scan-id"
