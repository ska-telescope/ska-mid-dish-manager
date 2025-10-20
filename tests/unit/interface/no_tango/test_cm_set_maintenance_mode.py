"""Tests dish manager component manager set_maintenance_mode command handler."""

import logging
from unittest.mock import Mock, patch

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.dish_enums import DishMode


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
def test_set_maintenance_mode_handler(
    caplog,
    component_manager: DishManagerComponentManager,
    mock_command_tracker: Mock,
    callbacks: dict,
) -> None:
    """Verify behaviour of SetMaintenanceMode command handler.

    :param component_manager: the component manager under test
    :param mock_command_tracker: representing the command tracker class
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    caplog.set_level(logging.DEBUG)
    component_manager.set_maintenance_mode(callbacks["task_cb"])
    # wait a bit for the lrc updates to come through
    component_state_cb = callbacks["comp_state_cb"]
    component_state_cb.get_queue_values()

    # TODO: Remove below. Waiting for SPFRx to implement maintenance mode
    assert "Nothing done on SPFRx, awaiting implementation on it." in caplog.text

    expected_call_kwargs = (
        {"status": TaskStatus.QUEUED},
        {"status": TaskStatus.IN_PROGRESS},
        {"progress": "Awaiting DS operatingmode change to STOW"},
        {"progress": "Awaiting SPFRX operatingmode change to STANDBY"},
        {"progress": "Awaiting SPF operatingmode change to MAINTENANCE"},
        {"progress": "Fanned out commands: DS.Stow, SPFRX.SetStandbyMode, SPF.SetMaintenanceMode"},
        {"progress": "Awaiting dishmode change to STOW"},
        {
            "progress": "SetMaintenanceMode completed",
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, "SetMaintenanceMode completed"),
        },
    )
    # check that the initial lrc updates come through
    actual_call_kwargs = callbacks["task_cb"].call_args_list
    for count, mock_call in enumerate(actual_call_kwargs):
        _, kwargs = mock_call
        assert kwargs == expected_call_kwargs[count]

    # check that the component state reports the requested command
    component_manager._update_component_state(dishmode=DishMode.STOW)
    component_state_cb.wait_for_value("dishmode", DishMode.STOW)

    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values()
    # check that the final lrc updates come through
    task_cb = callbacks["task_cb"]
    task_cb.assert_called_with(
        progress="SetMaintenanceMode completed",
        status=TaskStatus.COMPLETED,
        result=(ResultCode.OK, "SetMaintenanceMode completed"),
    )
