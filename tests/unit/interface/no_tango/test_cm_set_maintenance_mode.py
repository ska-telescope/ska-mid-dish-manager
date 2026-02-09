"""Tests dish manager component manager set_maintenance_mode command handler."""

import logging
from unittest.mock import Mock, patch

import pytest
from ska_control_model import ResultCode, TaskStatus
from ska_mid_dish_simulators.sim_enums import (
    SPFOperatingMode,
    SPFRxOperatingMode,
)

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
)


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
def test_set_maintenance_mode_handler(
    caplog,
    component_manager: DishManagerComponentManager,
    callbacks: dict,
) -> None:
    """Verify behaviour of SetMaintenanceMode command handler.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    caplog.set_level(logging.DEBUG)
    component_manager.set_maintenance_mode(callbacks["task_cb"])
    # wait a bit for the lrc updates to come through
    component_state_cb = callbacks["comp_state_cb"]

    expected_call_kwargs = (
        {"status": TaskStatus.QUEUED},
        {"status": TaskStatus.IN_PROGRESS},
        {
            "status": TaskStatus.COMPLETED,
            "result": (ResultCode.OK, "SetMaintenanceMode completed"),
        },
    )

    # check that the component state reports the requested command
    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        operatingmode=SPFRxOperatingMode.STANDBY
    )
    component_manager.sub_component_managers["SPF"]._update_component_state(
        operatingmode=SPFOperatingMode.MAINTENANCE
    )
    component_manager.sub_component_managers["DS"]._update_component_state(
        operatingmode=DSOperatingMode.STOW
    )
    component_manager._update_component_state(dishmode=DishMode.MAINTENANCE)
    component_state_cb.wait_for_value("dishmode", DishMode.MAINTENANCE)

    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values()

    # TODO: Remove below. Waiting for SPFRx to implement maintenance mode
    assert "Nothing done on SPFRx, awaiting implementation on it." in caplog.text

    # check that the initial lrc updates come through
    actual_call_kwargs = callbacks["task_cb"].call_args_list
    for count, mock_call in enumerate(actual_call_kwargs):
        _, kwargs = mock_call
        assert kwargs == expected_call_kwargs[count]

    msgs = [
        "Awaiting DS operatingmode change to STOW",
        "Awaiting SPFRX operatingmode change to STANDBY",
        "Awaiting SPF operatingmode change to MAINTENANCE",
        "Fanned out commands: DS.Stow, SPFRX.SetStandbyMode, SPF.SetMaintenanceMode",
        "Awaiting dishmode change to STOW",
        "SPFRX operatingmode changed to STANDBY",
        "SPFRX.SetStandbyMode completed",
        "DS operatingmode changed to STOW",
        "DS.Stow completed",
        "SPF operatingmode changed to MAINTENANCE",
        "SPF.SetMaintenanceMode completed",
    ]
    progress_cb = callbacks["progress_cb"]
    for msg in msgs:
        progress_cb.wait_for_args((msg,))
