"""Tests dish manager component manager setstandbylp command handler."""

from unittest.mock import Mock, patch

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    SPFOperatingMode,
    SPFRxOperatingMode,
)


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
@patch("json.dumps", Mock(return_value="mocked sub-device-command-ids"))
def test_set_standbylp_handler(
    component_manager: DishManagerComponentManager,
    mock_command_tracker: Mock,
    callbacks: dict,
) -> None:
    """Verify behaviour of SetStandbyLP command handler.

    :param component_manager: the component manager under test
    :param mock_command_tracker: a representing the command tracker class
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    component_manager.set_standby_lp_mode(callbacks["task_cb"])
    # wait a bit for the lrc updates to come through
    component_state_cb = callbacks["comp_state_cb"]
    component_state_cb.get_queue_values()

    expected_call_kwargs = (
        {"status": TaskStatus.QUEUED},
        {"status": TaskStatus.IN_PROGRESS},
        {"progress": f"SetStandbyLPMode called on SPF, ID {mock_command_tracker.new_command()}"},
        {"progress": "Awaiting SPF operatingmode change to STANDBY_LP"},
        {"progress": f"SetStandbyMode called on SPFRX, ID {mock_command_tracker.new_command()}"},
        {"progress": "Awaiting SPFRX operatingmode change to STANDBY"},
        {"progress": f"SetStandbyMode called on DS, ID {mock_command_tracker.new_command()}"},
        {"progress": "Awaiting DS operatingmode change to STANDBY"},
        {"progress": "Commands: mocked sub-device-command-ids"},
        {"progress": "Awaiting dishmode change to STANDBY_LP"},
    )

    # check that the initial lrc updates come through
    actual_call_kwargs = callbacks["task_cb"].call_args_list
    for count, mock_call in enumerate(actual_call_kwargs):
        _, kwargs = mock_call
        assert kwargs == expected_call_kwargs[count]

    # check that the component state reports the requested command
    component_manager.sub_component_managers["SPF"]._update_component_state(
        operatingmode=SPFOperatingMode.STANDBY_LP
    )
    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        operatingmode=SPFRxOperatingMode.STANDBY
    )
    component_manager.sub_component_managers["DS"]._update_component_state(
        operatingmode=DSOperatingMode.STANDBY
    )
    component_manager._update_component_state(dishmode=DishMode.STANDBY_LP)
    component_state_cb.wait_for_value("dishmode", DishMode.STANDBY_LP)

    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values()
    # check that the final lrc updates come through
    task_cb = callbacks["task_cb"]
    task_cb.assert_called_with(
        progress="SetStandbyLPMode completed",
        status=TaskStatus.COMPLETED,
        result=(ResultCode.OK, "SetStandbyLPMode completed"),
    )
