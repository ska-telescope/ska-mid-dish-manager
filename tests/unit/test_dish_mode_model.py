"""Unit tests verifying model against dishMode transitions."""

import pytest

from ska_mid_dish_manager.models.dish_enums import DishMode
from ska_mid_dish_manager.models.dish_mode_model import (
    CommandNotAllowed,
    DishModeModel,
    compute_dish_health_state,
    compute_dish_mode,
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
        ("STANDBY_LP", "SetStandbyFPMode", True),
        ("MAINTENANCE", "SetStandbyFPMode", True),
        ("OPERATE", "SetStandbyFPMode", True),
        ("STOW", "SetStandbyFPMode", True),
        ("STANDBY_FP", "SetStandbyFPMode", False),
        ("STARTUP", "SetStandbyFPMode", False),
        ("SHUTDOWN", "SetStandbyFPMode", False),
        ("STOW", "SetStowMode", False),
        ("STANDBY_FP", "SetStowMode", True),
        ("STANDBY_LP", "SetStowMode", True),
        ("MAINTENANCE", "SetStowMode", True),
        ("OPERATE", "SetStowMode", True),
        ("STARTUP", "SetStowMode", True),
        ("CONFIG", "SetStowMode", True),
        ("SHUTDOWN", "SetStowMode", True),
        ("STANDBY_FP", "SetOperateMode", True),
        ("OPERATE", "SetOperateMode", False),
        ("STANDBY_LP", "SetOperateMode", False),
        ("STARTUP", "SetOperateMode", False),
        ("STOW", "SetOperateMode", False),
        ("SHUTDOWN", "SetOperateMode", False),
        ("MAINTENANCE", "SetOperateMode", False),
        ("MAINTENANCE", "SetStandbyLPMode", True),
        ("STANDBY_FP", "SetStandbyLPMode", True),
        ("STANDBY_LP", "SetStandbyLPMode", False),
        ("STOW", "SetStandbyLPMode", True),
        ("SHUTDOWN", "SetStandbyLPMode", False),
        ("STARTUP", "SetStandbyLPMode", False),
        ("CONFIG", "SetStandbyLPMode", False),
        ("OPERATE", "SetStandbyLPMode", False),
        ("STANDBY_FP", "SetMaintenanceMode", True),
        ("MAINTENANCE", "SetMaintenanceMode", False),
        ("STANDBY_LP", "SetMaintenanceMode", True),
        ("OPERATE", "SetMaintenanceMode", False),
        ("CONFIG", "SetMaintenanceMode", False),
        ("STOW", "SetMaintenanceMode", False),
        ("STARTUP", "SetMaintenanceMode", False),
        ("SHUTDOWN", "SetMaintenanceMode", False),
        ("STANDBY_FP", "ConfigureBand1", True),
        ("STANDBY_FP", "ConfigureBand2", True),
        ("STANDBY_FP", "ConfigureBand3", True),
        ("STANDBY_FP", "ConfigureBand4", True),
        ("STANDBY_FP", "ConfigureBand5a", True),
        ("STANDBY_FP", "ConfigureBand5b", True),
        ("OPERATE", "ConfigureBand1", True),
        ("OPERATE", "ConfigureBand2", True),
        ("OPERATE", "ConfigureBand3", True),
        ("OPERATE", "ConfigureBand4", True),
        ("OPERATE", "ConfigureBand5a", True),
        ("OPERATE", "ConfigureBand5b", True),
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


@pytest.mark.parametrize(
    "subservient_devices_state,expected_dish_mode",
    [
        (
            {
                "ds_op_mode": "STANDBY_LP",
                "spf_op_mode": "STANDBY_LP",
                "spfrx_op_mode": "STANDBY",
                "ds_pow_state": "LOW_POWER",
                "spf_pow_state": "LOW_POWER",
                "spfrx_pow_state": "LOW_POWER",
            },
            "STANDBY_LP",
        ),
        (
            {
                "ds_op_mode": "STANDBY_FP",
                "spf_op_mode": "OPERATE",
                "spfrx_op_mode": "STANDBY",
                "ds_pow_state": "FULL_POWER",
                "spf_pow_state": "FULL_POWER",
                "spfrx_pow_state": "FULL_POWER",
            },
            "STANDBY_FP",
        ),
        (
            {
                "ds_op_mode": "STANDBY_FP",
                "spf_op_mode": "OPERATE",
                "spfrx_op_mode": "DATA_CAPTURE",
                "ds_pow_state": "FULL_POWER",
                "spf_pow_state": "FULL_POWER",
                "spfrx_pow_state": "FULL_POWER",
            },
            "STANDBY_FP",
        ),
        (
            {
                "ds_op_mode": "POINT",
                "spf_op_mode": "OPERATE",
                "spfrx_op_mode": "DATA_CAPTURE",
                "ds_pow_state": "FULL_POWER",
                "spf_pow_state": "FULL_POWER",
                "spfrx_pow_state": "FULL_POWER",
            },
            "OPERATE",
        ),
    ],
)
def test_compute_dish_mode(subservient_devices_state, expected_dish_mode):
    actual_dish_mode = compute_dish_mode(subservient_devices_state)
    assert expected_dish_mode == actual_dish_mode


@pytest.mark.parametrize(
    "subservient_health_states,expected_dish_health_state",
    [
        (
            {
                "ds_health_state": "OK",
                "spf_health_state": "OK",
                "spfrx_health_state": "OK",
            },
            "OK",
        ),
        (
            {
                "ds_health_state": "DEGRADED",
                "spf_health_state": "DEGRADED",
                "spfrx_health_state": "DEGRADED",
            },
            "DEGRADED",
        ),
        (
            {
                "ds_health_state": "FAILED",
                "spf_health_state": "FAILED",
                "spfrx_health_state": "FAILED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "UNKNOWN",
                "spf_health_state": "UNKNOWN",
                "spfrx_health_state": "UNKNOWN",
            },
            "UNKNOWN",
        ),
        (
            {
                "ds_health_state": "DEGRADED",
                "spf_health_state": "OK",
                "spfrx_health_state": "OK",
            },
            "DEGRADED",
        ),
        (
            {
                "ds_health_state": "FAILED",
                "spf_health_state": "OK",
                "spfrx_health_state": "OK",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "UNKNOWN",
                "spf_health_state": "OK",
                "spfrx_health_state": "OK",
            },
            "UNKNOWN",
        ),
        (
            {
                "ds_health_state": "OK",
                "spf_health_state": "DEGRADED",
                "spfrx_health_state": "OK",
            },
            "DEGRADED",
        ),
        (
            {
                "ds_health_state": "OK",
                "spf_health_state": "FAILED",
                "spfrx_health_state": "OK",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "OK",
                "spf_health_state": "UNKNOWN",
                "spfrx_health_state": "OK",
            },
            "UNKNOWN",
        ),
        (
            {
                "ds_health_state": "OK",
                "spf_health_state": "OK",
                "spfrx_health_state": "DEGRADED",
            },
            "DEGRADED",
        ),
        (
            {
                "ds_health_state": "OK",
                "spf_health_state": "OK",
                "spfrx_health_state": "FAILED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "OK",
                "spf_health_state": "OK",
                "spfrx_health_state": "UNKNOWN",
            },
            "UNKNOWN",
        ),
        (
            {
                "ds_health_state": "OK",
                "spf_health_state": "DEGRADED",
                "spfrx_health_state": "DEGRADED",
            },
            "DEGRADED",
        ),
        (
            {
                "ds_health_state": "FAILED",
                "spf_health_state": "DEGRADED",
                "spfrx_health_state": "DEGRADED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "UNKNOWN",
                "spf_health_state": "DEGRADED",
                "spfrx_health_state": "DEGRADED",
            },
            "DEGRADED",
        ),
        (
            {
                "ds_health_state": "DEGRADED",
                "spf_health_state": "OK",
                "spfrx_health_state": "DEGRADED",
            },
            "DEGRADED",
        ),
        (
            {
                "ds_health_state": "DEGRADED",
                "spf_health_state": "FAILED",
                "spfrx_health_state": "DEGRADED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "DEGRADED",
                "spf_health_state": "UNKNOWN",
                "spfrx_health_state": "DEGRADED",
            },
            "DEGRADED",
        ),
        (
            {
                "ds_health_state": "DEGRADED",
                "spf_health_state": "DEGRADED",
                "spfrx_health_state": "OK",
            },
            "DEGRADED",
        ),
        (
            {
                "ds_health_state": "DEGRADED",
                "spf_health_state": "DEGRADED",
                "spfrx_health_state": "FAILED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "DEGRADED",
                "spf_health_state": "DEGRADED",
                "spfrx_health_state": "UNKNOWN",
            },
            "DEGRADED",
        ),
        (
            {
                "ds_health_state": "OK",
                "spf_health_state": "UNKNOWN",
                "spfrx_health_state": "UNKNOWN",
            },
            "UNKNOWN",
        ),
        (
            {
                "ds_health_state": "FAILED",
                "spf_health_state": "UNKNOWN",
                "spfrx_health_state": "UNKNOWN",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "DEGRADED",
                "spf_health_state": "UNKNOWN",
                "spfrx_health_state": "UNKNOWN",
            },
            "DEGRADED",
        ),
        (
            {
                "ds_health_state": "UNKNOWN",
                "spf_health_state": "OK",
                "spfrx_health_state": "UNKNOWN",
            },
            "UNKNOWN",
        ),
        (
            {
                "ds_health_state": "UNKNOWN",
                "spf_health_state": "FAILED",
                "spfrx_health_state": "UNKNOWN",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "UNKNOWN",
                "spf_health_state": "DEGRADED",
                "spfrx_health_state": "UNKNOWN",
            },
            "DEGRADED",
        ),
        (
            {
                "ds_health_state": "UNKNOWN",
                "spf_health_state": "UNKNOWN",
                "spfrx_health_state": "OK",
            },
            "UNKNOWN",
        ),
        (
            {
                "ds_health_state": "UNKNOWN",
                "spf_health_state": "UNKNOWN",
                "spfrx_health_state": "FAILED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "UNKNOWN",
                "spf_health_state": "UNKNOWN",
                "spfrx_health_state": "DEGRADED",
            },
            "DEGRADED",
        ),
        (
            {
                "ds_health_state": "OK",
                "spf_health_state": "FAILED",
                "spfrx_health_state": "FAILED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "DEGRADED",
                "spf_health_state": "FAILED",
                "spfrx_health_state": "FAILED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "UNKNOWN",
                "spf_health_state": "FAILED",
                "spfrx_health_state": "FAILED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "FAILED",
                "spf_health_state": "OK",
                "spfrx_health_state": "FAILED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "FAILED",
                "spf_health_state": "DEGRADED",
                "spfrx_health_state": "FAILED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "FAILED",
                "spf_health_state": "UNKNOWN",
                "spfrx_health_state": "FAILED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "FAILED",
                "spf_health_state": "FAILED",
                "spfrx_health_state": "OK",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "FAILED",
                "spf_health_state": "FAILED",
                "spfrx_health_state": "DEGRADED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "FAILED",
                "spf_health_state": "FAILED",
                "spfrx_health_state": "UNKNOWN",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "OK",
                "spf_health_state": "DEGRADED",
                "spfrx_health_state": "UNKNOWN",
            },
            "DEGRADED",
        ),
        (
            {
                "ds_health_state": "OK",
                "spf_health_state": "FAILED",
                "spfrx_health_state": "UNKNOWN",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "OK",
                "spf_health_state": "FAILED",
                "spfrx_health_state": "DEGRADED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "OK",
                "spf_health_state": "UNKNOWN",
                "spfrx_health_state": "DEGRADED",
            },
            "DEGRADED",
        ),
        (
            {
                "ds_health_state": "OK",
                "spf_health_state": "UNKNOWN",
                "spfrx_health_state": "FAILED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "OK",
                "spf_health_state": "DEGRADED",
                "spfrx_health_state": "FAILED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "DEGRADED",
                "spf_health_state": "OK",
                "spfrx_health_state": "UNKNOWN",
            },
            "DEGRADED",
        ),
        (
            {
                "ds_health_state": "FAILED",
                "spf_health_state": "OK",
                "spfrx_health_state": "UNKNOWN",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "FAILED",
                "spf_health_state": "OK",
                "spfrx_health_state": "DEGRADED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "UNKNOWN",
                "spf_health_state": "OK",
                "spfrx_health_state": "DEGRADED",
            },
            "DEGRADED",
        ),
        (
            {
                "ds_health_state": "UNKNOWN",
                "spf_health_state": "OK",
                "spfrx_health_state": "FAILED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "DEGRADED",
                "spf_health_state": "OK",
                "spfrx_health_state": "FAILED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "DEGRADED",
                "spf_health_state": "UNKNOWN",
                "spfrx_health_state": "OK",
            },
            "DEGRADED",
        ),
        (
            {
                "ds_health_state": "FAILED",
                "spf_health_state": "UNKNOWN",
                "spfrx_health_state": "OK",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "FAILED",
                "spf_health_state": "DEGRADED",
                "spfrx_health_state": "OK",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "UNKNOWN",
                "spf_health_state": "DEGRADED",
                "spfrx_health_state": "OK",
            },
            "DEGRADED",
        ),
        (
            {
                "ds_health_state": "UNKNOWN",
                "spf_health_state": "FAILED",
                "spfrx_health_state": "OK",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "DEGRADED",
                "spf_health_state": "FAILED",
                "spfrx_health_state": "OK",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "DEGRADED",
                "spf_health_state": "FAILED",
                "spfrx_health_state": "UNKNOWN",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "DEGRADED",
                "spf_health_state": "UNKNOWN",
                "spfrx_health_state": "FAILED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "FAILED",
                "spf_health_state": "DEGRADED",
                "spfrx_health_state": "UNKNOWN",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "UNKNOWN",
                "spf_health_state": "DEGRADED",
                "spfrx_health_state": "FAILED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "FAILED",
                "spf_health_state": "UNKNOWN",
                "spfrx_health_state": "DEGRADED",
            },
            "FAILED",
        ),
        (
            {
                "ds_health_state": "UNKNOWN",
                "spf_health_state": "FAILED",
                "spfrx_health_state": "DEGRADED",
            },
            "FAILED",
        ),
    ],
)
def test_compute_dish_health_state(
    subservient_health_states, expected_dish_health_state
):
    actual_dish_health_state = compute_dish_health_state(
        subservient_health_states
    )
    assert expected_dish_health_state == actual_dish_health_state
