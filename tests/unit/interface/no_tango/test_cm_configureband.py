"""Tests dish manager component manager configureband command handler."""

from unittest.mock import Mock, patch

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.dish_enums import Band


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
@patch("json.dumps", Mock(return_value="mocked sub-device-command-ids"))
def test_configureband_handler(
    component_manager: DishManagerComponentManager,
    mock_command_tracker: Mock,
    callbacks: dict,
) -> None:
    """Verify behaviour of ConfigureBand[x] command handler.

    :param component_manager: the component manager under test
    :param mock_command_tracker: a representing the command tracker class
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    component_state_cb = callbacks["comp_state_cb"]
    component_manager.configure_band_cmd(2, True, callbacks["task_cb"])
    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values()

    expected_call_kwargs = (
        {"status": TaskStatus.QUEUED},
        {"status": TaskStatus.IN_PROGRESS},
        {"progress": f"SetIndexPosition called on DS, ID {mock_command_tracker.new_command()}"},
        {"progress": "Awaiting DS indexerposition change to B2"},
        {"progress": f"ConfigureBand2 called on SPFRX, ID {mock_command_tracker.new_command()}"},
        {"progress": "Awaiting SPFRX configuredband change to B2"},
        {"progress": "Commands: mocked sub-device-command-ids"},
        {"progress": "Awaiting configuredband change to B2"},
    )

    # check that the initial lrc updates come through
    actual_call_kwargs = callbacks["task_cb"].call_args_list
    for count, mock_call in enumerate(actual_call_kwargs):
        _, kwargs = mock_call
        assert kwargs == expected_call_kwargs[count]

    # check that the component state reports the requested command
    component_manager._update_component_state(configuredband=Band.B2)
    component_state_cb.wait_for_value("configuredband", Band.B2)

    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values()
    # check that the final lrc updates come through
    task_cb = callbacks["task_cb"]
    task_cb.assert_called_with(
        progress="ConfigureBand2 completed",
        status=TaskStatus.COMPLETED,
        result=(ResultCode.OK, "ConfigureBand2 completed"),
    )
