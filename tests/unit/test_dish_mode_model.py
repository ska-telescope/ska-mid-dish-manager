import pytest

from ska_mid_dish_manager.models.dish_enums import DishMode
from ska_mid_dish_manager.models.dish_mode_model import (
    CommandNotAllowed,
    DishModeModel,
)


@pytest.fixture(scope="module")
def dish_mode_model():
    return DishModeModel()


def test_node_count(dish_mode_model):
    assert dish_mode_model.dishmode_graph.number_of_nodes() == len(
        DishMode
    ), "Mode model nodes number not equal to DishMode enums"

    for dish_mode_enum in DishMode:
        assert dish_mode_enum.name in dish_mode_model.dishmode_graph.nodes


@pytest.mark.parametrize(
    "current_mode,requested_command,is_allowed",
    [
        ("STANDBY_FP", "SetOperateMode", True),
        ("STANDBY_LP", "SetOperateMode", False),
        ("MAINTENANCE", "SetStandbyLPMode", True),
    ],
)
def test_is_mode_transition_allowed(
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
