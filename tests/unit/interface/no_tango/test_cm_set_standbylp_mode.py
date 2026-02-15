"""Tests dish manager component manager setstandbylp command handler."""

from unittest.mock import Mock, patch

import pytest
from ska_control_model import ResultCode, TaskStatus
from ska_mid_dish_utils.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    DSPowerState,
    SPFOperatingMode,
    SPFRxOperatingMode,
)

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
def test_set_standbylp_handler(
    component_manager: DishManagerComponentManager,
    callbacks: dict,
) -> None:
    """Verify behaviour of SetStandbyLP command handler.

    :param component_manager: the component manager under test
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
    )

    # check that the initial lrc updates come through
    actual_call_kwargs = callbacks["task_cb"].call_args_list
    for count, mock_call in enumerate(actual_call_kwargs):
        _, kwargs = mock_call
        assert kwargs == expected_call_kwargs[count]

    progress_cb = callbacks["progress_cb"]
    expected_progress_updates = [
        "Awaiting SPF operatingmode change to STANDBY_LP",
        "Awaiting SPFRX operatingmode change to STANDBY",
        "Awaiting DS operatingmode, powerstate change to STANDBY, LOW_POWER",
        "Fanned out commands: SPF.SetStandbyLPMode, SPFRX.SetStandbyMode, DS.SetStandbyMode",
        "Awaiting dishmode change to STANDBY_LP",
    ]
    progress_updates = progress_cb.get_args_queue()
    for msg in expected_progress_updates:
        assert (msg,) in progress_updates

    # check that the component state reports the requested command
    component_manager.sub_component_managers["SPF"]._update_component_state(
        operatingmode=SPFOperatingMode.STANDBY_LP
    )
    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        operatingmode=SPFRxOperatingMode.STANDBY
    )
    component_manager.sub_component_managers["DS"]._update_component_state(
        operatingmode=DSOperatingMode.STANDBY, powerstate=DSPowerState.LOW_POWER
    )
    component_state_cb.wait_for_value("dishmode", DishMode.STANDBY_LP)

    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values()
    # check that the final lrc updates come through
    task_cb = callbacks["task_cb"]
    task_cb.assert_called_with(
        status=TaskStatus.COMPLETED,
        result=(ResultCode.OK, "SetStandbyLPMode completed"),
    )
    progress_cb.wait_for_args(("SetStandbyLPMode completed",))
