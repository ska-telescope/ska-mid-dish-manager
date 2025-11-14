"""Tests dish manager component manager setstandbyfp command handler."""

from unittest.mock import Mock, patch

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.dish_enums import DishMode, DSOperatingMode, DSPowerState


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
def test_set_standbyfp_handler(
    component_manager: DishManagerComponentManager,
    callbacks: dict,
) -> None:
    """Verify behaviour of SetStandbyFP command handler.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    component_manager.set_standby_fp_mode(callbacks["task_cb"])
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
    progress_cb.wait_for_args(("Awaiting DS operatingmode change to STANDBY",))
    progress_cb.wait_for_args(("Awaiting DS powerstate change to FULL_POWER",))
    progress_cb.wait_for_args(("Fanned out commands: DS.SetStandbyMode, DS.SetPowerMode",))
    progress_cb.wait_for_args(("Awaiting dishmode change to STANDBY_FP",))

    # check that the component state reports the requested command
    component_manager.sub_component_managers["DS"]._update_component_state(
        operatingmode=DSOperatingMode.STANDBY, powerstate=DSPowerState.FULL_POWER
    )
    component_state_cb.wait_for_value("dishmode", DishMode.STANDBY_FP)

    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values()
    # check that the final lrc updates come through
    task_cb = callbacks["task_cb"]
    task_cb.assert_called_with(
        status=TaskStatus.COMPLETED,
        result=(ResultCode.OK, "SetStandbyFPMode completed"),
    )
    progress_cb.wait_for_args(("SetStandbyFPMode completed",))
