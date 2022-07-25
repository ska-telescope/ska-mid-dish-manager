"""Unit tests verifying model against dishMode transitions."""

import pytest

from ska_mid_dish_manager.models.dish_enums import DishMode
from ska_mid_dish_manager.models.dish_mode_model import (
    CommandNotAllowed,
    DishModeModel,
)


# pylint: disable=missing-function-docstring, redefined-outer-name
@pytest.fixture(scope="module")
def dish_mode_model():
    return DishModeModel()


def test_model_node_matches_dish_mode_enums(dish_mode_model):
    assert dish_mode_model.dishmode_graph.number_of_nodes() == len(
        DishMode
    ), "Nodes on DishMode model are not equal to DishMode enums"

    for dish_mode_enum in DishMode:
        assert dish_mode_enum.name in dish_mode_model.dishmode_graph.nodes


@pytest.mark.parametrize(
    "current_mode,requested_command,is_allowed",
    [
        ("STANDBY_FP", "SetOperateMode", True),
        ("OPERATE", "SetOperateMode", True),
        ("STANDBY_LP", "SetOperateMode", False),
        ("STARTUP", "SetOperateMode", False),
        ("STOW", "SetOperateMode", False),
        ("SHUTDOWN", "SetOperateMode", False),
        ("CONFIG", "SetOperateMode", False),
        ("MAINTENANCE", "SetOperateMode", False),
        ("MAINTENANCE", "SetStandbyLPMode", True),
        ("STANDBY_FP", "SetStandbyLPMode", True),
        ("STANDBY_LP", "SetStandbyLPMode", True),
        ("STOW", "SetStandbyLPMode", True),
        ("SHUTDOWN", "SetStandbyLPMode", False),
        ("STARTUP", "SetStandbyLPMode", False),
        ("CONFIG", "SetStandbyLPMode", False),
        ("OPERATE", "SetStandbyLPMode", False),
        ("STANDBY_FP", "SetMaintenanceMode", True),
        ("MAINTENANCE", "SetMaintenanceMode", True),
        ("STANDBY_LP", "SetMaintenanceMode", True),
        ("OPERATE", "SetMaintenanceMode", False),
        ("CONFIG", "SetMaintenanceMode", False),
        ("STOW", "SetMaintenanceMode", False),
        ("STARTUP", "SetMaintenanceMode", False),
        ("SHUTDOWN", "SetMaintenanceMode", False),
        ("STANDBY_FP", "SetStandbyFPMode", True),
        ("STANDBY_LP", "SetStandbyFPMode", True),
        ("MAINTENANCE", "SetStandbyFPMode", True),
        ("OPERATE", "SetStandbyFPMode", True),
        ("STOW", "SetStandbyFPMode", True),
        ("CONFIG", "SetStandbyFPMode", False),
        ("STARTUP", "SetStandbyFPMode", False),
        ("SHUTDOWN", "SetStandbyFPMode", False),
        ("STOW", "SetStowMode", True),  
    ],
)
def test_model_dish_mode_transition_accuracy(
    dish_mode_model, current_mode, requested_command, is_allowed
):
    if is_allowed:
        assert (
            dish_mode_model.is_command_allowed(
                dish_mode=current_mode, command_name=requested_command
            )
            == is_allowed
        )
    else:
        with pytest.raises(CommandNotAllowed):
            dish_mode_model.is_command_allowed(
                dish_mode=current_mode, command_name=requested_command
            )
