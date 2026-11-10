"""Unit tests verifying model against dishMode transitions."""

import pytest

from ska_mid_dish_manager.models.dish_enums import DishMode
from ska_mid_dish_manager.models.dish_mode_model import CommandNotAllowedError, DishModeModel


@pytest.fixture(scope="module")
def dish_mode_model():
    return DishModeModel()


@pytest.mark.unit
def test_model_node_matches_dish_mode_enums(dish_mode_model):
    assert dish_mode_model.dishmode_graph.number_of_nodes() == len(DishMode), (
        "Nodes on DishMode model are not equal to DishMode enums"
    )

    for dish_mode_enum in DishMode:
        assert dish_mode_enum.name in dish_mode_model.dishmode_graph.nodes


@pytest.mark.unit
@pytest.mark.parametrize(
    "current_mode,requested_command",
    [
        ("SHUTDOWN", "SetStowMode"),
        ("STARTUP", "SetStowMode"),
        ("STARTUP", "SetMaintenanceMode"),
        ("STANDBY_LP", "SetStandbyFPMode"),
        ("STANDBY_LP", "SetStowMode"),
        ("STANDBY_LP", "SetMaintenanceMode"),
        ("STANDBY_LP", "ConfigureBand1"),
        ("STANDBY_LP", "ConfigureBand2"),
        ("STANDBY_LP", "ConfigureBand3"),
        ("STANDBY_LP", "ConfigureBand4"),
        ("STANDBY_LP", "ConfigureBand5a"),
        ("STANDBY_LP", "ConfigureBand5b"),
        ("STANDBY_LP", "ConfigureBand"),
        ("STANDBY_FP", "SetStowMode"),
        ("STANDBY_FP", "SetStandbyLPMode"),
        ("STANDBY_FP", "SetMaintenanceMode"),
        ("STANDBY_FP", "ConfigureBand1"),
        ("STANDBY_FP", "ConfigureBand2"),
        ("STANDBY_FP", "ConfigureBand3"),
        ("STANDBY_FP", "ConfigureBand4"),
        ("STANDBY_FP", "ConfigureBand5a"),
        ("STANDBY_FP", "ConfigureBand5b"),
        ("STANDBY_FP", "ConfigureBand"),
        ("MAINTENANCE", "SetStowMode"),
        ("STOW", "SetStandbyFPMode"),
        ("STOW", "SetStandbyLPMode"),
        ("STOW", "SetMaintenanceMode"),
        ("STOW", "ConfigureBand1"),
        ("STOW", "ConfigureBand2"),
        ("STOW", "ConfigureBand3"),
        ("STOW", "ConfigureBand4"),
        ("STOW", "ConfigureBand5a"),
        ("STOW", "ConfigureBand5b"),
        ("STOW", "ConfigureBand"),
        ("CONFIG", "SetStowMode"),
        ("CONFIG", "SetMaintenanceMode"),
        ("OPERATE", "SetStandbyFPMode"),
        ("OPERATE", "SetStowMode"),
        ("OPERATE", "SetStandbyLPMode"),
        ("OPERATE", "SetMaintenanceMode"),
        ("OPERATE", "ConfigureBand1"),
        ("OPERATE", "ConfigureBand2"),
        ("OPERATE", "ConfigureBand3"),
        ("OPERATE", "ConfigureBand4"),
        ("OPERATE", "ConfigureBand5a"),
        ("OPERATE", "ConfigureBand5b"),
        ("OPERATE", "ConfigureBand"),
    ],
)
def test_model_dish_mode_transition_accuracy(dish_mode_model, current_mode, requested_command):
    actual_response = dish_mode_model.is_command_allowed(
        requested_command,
        component_state={"dishmode": current_mode},
    )
    assert actual_response is True


@pytest.mark.unit
@pytest.mark.parametrize(
    "current_mode,requested_command",
    [
        ("SHUTDOWN", "SetStandbyFPMode"),
        ("SHUTDOWN", "SetStandbyLPMode"),
        ("SHUTDOWN", "ConfigureBand1"),
        ("SHUTDOWN", "ConfigureBand2"),
        ("SHUTDOWN", "ConfigureBand3"),
        ("SHUTDOWN", "ConfigureBand4"),
        ("SHUTDOWN", "ConfigureBand5a"),
        ("SHUTDOWN", "ConfigureBand5b"),
        ("SHUTDOWN", "ConfigureBand"),
        ("STARTUP", "SetStandbyFPMode"),
        ("STARTUP", "SetStandbyLPMode"),
        ("STARTUP", "ConfigureBand1"),
        ("STARTUP", "ConfigureBand2"),
        ("STARTUP", "ConfigureBand3"),
        ("STARTUP", "ConfigureBand4"),
        ("STARTUP", "ConfigureBand5a"),
        ("STARTUP", "ConfigureBand5b"),
        ("STARTUP", "ConfigureBand"),
        ("STANDBY_LP", "SetStandbyLPMode"),
        ("STANDBY_FP", "SetStandbyFPMode"),
        ("MAINTENANCE", "SetStandbyFPMode"),
        ("MAINTENANCE", "SetStandbyLPMode"),
        ("MAINTENANCE", "SetMaintenanceMode"),
        ("MAINTENANCE", "ConfigureBand1"),
        ("MAINTENANCE", "ConfigureBand2"),
        ("MAINTENANCE", "ConfigureBand3"),
        ("MAINTENANCE", "ConfigureBand4"),
        ("MAINTENANCE", "ConfigureBand5a"),
        ("MAINTENANCE", "ConfigureBand5b"),
        ("MAINTENANCE", "ConfigureBand"),
        ("STOW", "SetStowMode"),
        ("CONFIG", "SetStandbyLPMode"),
        ("CONFIG", "SetStandbyFPMode"),
        ("CONFIG", "ConfigureBand1"),
        ("CONFIG", "ConfigureBand2"),
        ("CONFIG", "ConfigureBand3"),
        ("CONFIG", "ConfigureBand4"),
        ("CONFIG", "ConfigureBand5a"),
        ("CONFIG", "ConfigureBand5b"),
        ("CONFIG", "ConfigureBand"),
    ],
)
def test_model_dish_mode_transition_not_allowed(dish_mode_model, current_mode, requested_command):
    with pytest.raises(CommandNotAllowedError):
        dish_mode_model.is_command_allowed(
            requested_command,
            component_state={"dishmode": current_mode},
        )
