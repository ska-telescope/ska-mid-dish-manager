"""Unit tests verifying model against dishMode transitions."""

import pytest

from ska_mid_dish_manager.models.dish_enums import DishMode
from ska_mid_dish_manager.models.dish_mode_model import DishModeModel


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
    "current_mode,requested_command,expected_response",
    [
        ("SHUTDOWN", "SetStandbyFPMode", False),
        ("SHUTDOWN", "SetStowMode", True),
        ("SHUTDOWN", "SetStandbyLPMode", False),
        ("SHUTDOWN", "ConfigureBand1", False),
        ("SHUTDOWN", "ConfigureBand2", False),
        ("SHUTDOWN", "ConfigureBand3", False),
        ("SHUTDOWN", "ConfigureBand4", False),
        ("SHUTDOWN", "ConfigureBand5a", False),
        ("SHUTDOWN", "ConfigureBand5b", False),
        ("STARTUP", "SetStandbyFPMode", False),
        ("STARTUP", "SetStowMode", True),
        ("STARTUP", "SetStandbyLPMode", False),
        ("STARTUP", "SetMaintenanceMode", True),
        ("STARTUP", "ConfigureBand1", False),
        ("STARTUP", "ConfigureBand2", False),
        ("STARTUP", "ConfigureBand3", False),
        ("STARTUP", "ConfigureBand4", False),
        ("STARTUP", "ConfigureBand5a", False),
        ("STARTUP", "ConfigureBand5b", False),
        ("STANDBY_LP", "SetStandbyFPMode", True),
        ("STANDBY_LP", "SetStowMode", True),
        ("STANDBY_LP", "SetStandbyLPMode", False),
        ("STANDBY_LP", "SetMaintenanceMode", True),
        ("STANDBY_LP", "ConfigureBand1", True),
        ("STANDBY_LP", "ConfigureBand2", True),
        ("STANDBY_LP", "ConfigureBand3", True),
        ("STANDBY_LP", "ConfigureBand4", True),
        ("STANDBY_LP", "ConfigureBand5a", True),
        ("STANDBY_LP", "ConfigureBand5b", True),
        ("STANDBY_FP", "SetStandbyFPMode", False),
        ("STANDBY_FP", "SetStowMode", True),
        ("STANDBY_FP", "SetStandbyLPMode", True),
        ("STANDBY_FP", "SetMaintenanceMode", True),
        ("STANDBY_FP", "ConfigureBand1", True),
        ("STANDBY_FP", "ConfigureBand2", True),
        ("STANDBY_FP", "ConfigureBand3", True),
        ("STANDBY_FP", "ConfigureBand4", True),
        ("STANDBY_FP", "ConfigureBand5a", True),
        ("STANDBY_FP", "ConfigureBand5b", True),
        ("MAINTENANCE", "SetStandbyFPMode", False),
        ("MAINTENANCE", "SetStowMode", True),
        ("MAINTENANCE", "SetStandbyLPMode", False),
        ("MAINTENANCE", "SetMaintenanceMode", False),
        ("MAINTENANCE", "ConfigureBand1", False),
        ("MAINTENANCE", "ConfigureBand2", False),
        ("MAINTENANCE", "ConfigureBand3", False),
        ("MAINTENANCE", "ConfigureBand4", False),
        ("MAINTENANCE", "ConfigureBand5a", False),
        ("MAINTENANCE", "ConfigureBand5b", False),
        ("STOW", "SetStandbyFPMode", True),
        ("STOW", "SetStowMode", False),
        ("STOW", "SetStandbyLPMode", True),
        ("STOW", "SetMaintenanceMode", True),
        ("STOW", "ConfigureBand1", True),
        ("STOW", "ConfigureBand2", True),
        ("STOW", "ConfigureBand3", True),
        ("STOW", "ConfigureBand4", True),
        ("STOW", "ConfigureBand5a", True),
        ("STOW", "ConfigureBand5b", True),
        ("CONFIG", "SetStowMode", True),
        ("CONFIG", "SetStandbyLPMode", False),  # Only auto transition allowed
        ("CONFIG", "SetMaintenanceMode", True),
        ("CONFIG", "SetStandbyFPMode", False),  # Only auto transition allowed
        ("CONFIG", "ConfigureBand1", False),
        ("CONFIG", "ConfigureBand2", False),
        ("CONFIG", "ConfigureBand3", False),
        ("CONFIG", "ConfigureBand4", False),
        ("CONFIG", "ConfigureBand5a", False),
        ("CONFIG", "ConfigureBand5b", False),
        ("OPERATE", "SetStandbyFPMode", True),
        ("OPERATE", "SetStowMode", True),
        ("OPERATE", "SetStandbyLPMode", True),
        ("OPERATE", "SetMaintenanceMode", True),
        ("OPERATE", "ConfigureBand1", True),
        ("OPERATE", "ConfigureBand2", True),
        ("OPERATE", "ConfigureBand3", True),
        ("OPERATE", "ConfigureBand4", True),
        ("OPERATE", "ConfigureBand5a", True),
        ("OPERATE", "ConfigureBand5b", True),
    ],
)
def test_model_dish_mode_transition_accuracy(
    dish_mode_model, current_mode, requested_command, expected_response
):
    actual_response = dish_mode_model.is_command_allowed(
        requested_command,
        dish_mode=current_mode,
    )
    assert actual_response == expected_response
