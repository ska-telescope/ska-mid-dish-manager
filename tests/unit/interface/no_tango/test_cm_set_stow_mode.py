"""Tests dish manager component manager setstow command handler."""

from unittest.mock import Mock, patch

import pytest
from ska_control_model import TaskStatus
from ska_mid_dish_utils.models.dish_enums import DishMode

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager


@pytest.mark.unit
@patch(
    "ska_mid_dish_manager.models.dish_mode_model.DishModeModel.is_command_allowed",
    Mock(return_value=True),
)
def test_set_stow_mode_handler(
    component_manager: DishManagerComponentManager,
    callbacks: dict,
) -> None:
    """Verify behaviour of SetStowMode command handler.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks, passed as callbacks to
        the command tracker under test
    """
    component_manager.set_stow_mode(callbacks["task_cb"])
    # wait a bit for the lrc updates to come through
    component_state_cb = callbacks["comp_state_cb"]
    component_state_cb.get_queue_values()

    expected_call_kwargs = ({"status": TaskStatus.COMPLETED},)

    # check that the initial lrc updates come through
    actual_call_kwargs = callbacks["task_cb"].call_args_list
    for count, mock_call in enumerate(actual_call_kwargs):
        _, kwargs = mock_call
        assert kwargs == expected_call_kwargs[count]

    progress_cb = callbacks["progress_cb"]
    progress_cb.wait_for_args(("Stow called, monitor dishmode for LRC completed",))
    # check that the component state reports the requested command
    component_manager._update_component_state(dishmode=DishMode.STOW)
    component_state_cb.wait_for_value("dishmode", DishMode.STOW)
