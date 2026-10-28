"""Test DishManagerComponentManager's control mode handling."""

from unittest.mock import patch

import pytest
from pytest_mock import MockerFixture
from ska_control_model.future import ControlMode

from ska_mid_dish_manager.component_managers.dish_manager_cm import (
    DishManagerComponentManager,
)
from ska_mid_dish_manager.models.constants import OPERATOR_TAG


@pytest.mark.unit
@pytest.mark.parametrize(
    "device",
    ["SPF", "SPFRX"],
)
@pytest.mark.parametrize(
    "mode",
    [
        ControlMode.NO_MONITOR_NO_CONTROL,
        ControlMode.MONITOR_AND_CONTROL,
    ],
)
def test_validate_subdevice_control_mode_valid(
    component_manager: DishManagerComponentManager,
    device: str,
    mode: ControlMode,
):
    """Test that supported control modes are accepted."""
    component_manager._validate_subdevice_control_mode(
        device,
        mode,
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "device",
    ["SPF", "SPFRX"],
)
def test_validate_subdevice_control_mode_unsupported(
    component_manager: DishManagerComponentManager,
    device: str,
):
    """Test that MONITOR_NO_CONTROL is rejected."""
    with pytest.raises(
        NotImplementedError,
        match="MONITOR_NO_CONTROL is not implemented",
    ):
        component_manager._validate_subdevice_control_mode(
            device,
            ControlMode.MONITOR_NO_CONTROL,
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "mode",
    [99, "INVALID", "2", None],
)
def test_validate_subdevice_control_mode_invalid(
    component_manager: DishManagerComponentManager,
    mode: ControlMode,
):
    """Test that invalid values are rejected."""
    with pytest.raises(ValueError):
        component_manager._validate_subdevice_control_mode(
            "SPF",
            mode,
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "device, setter_name, state_key",
    [
        ("SPF", "set_spf_control_mode", "spfcontrolmode"),
        ("SPFRX", "set_spfrx_control_mode", "spfrxcontrolmode"),
    ],
)
def test_setting_existing_control_mode(
    component_manager: DishManagerComponentManager,
    device: str,
    setter_name: str,
    state_key: str,
):
    """Verify repeated control mode requests do not change communication."""
    mode = ControlMode.NO_MONITOR_NO_CONTROL

    component_manager._update_component_state(**{state_key: mode})

    subdevice_cm = component_manager.sub_component_managers[device]

    setter = getattr(component_manager, setter_name)

    with (
        patch.object(component_manager.logger, "warning") as mock_warning,
        patch.object(subdevice_cm, "stop_communicating") as mock_stop,
        patch.object(subdevice_cm, "start_communicating") as mock_start,
        patch.object(component_manager, "sync_component_states") as mock_sync,
    ):
        setter(mode)

    mock_warning.assert_called_once()
    assert "already in" in mock_warning.call_args.args[0]

    mock_stop.assert_not_called()
    mock_start.assert_not_called()
    mock_sync.assert_not_called()

    assert component_manager.component_state[state_key] == mode


@pytest.mark.unit
def test_setting_existing_b5dc_control_mode(
    component_manager: DishManagerComponentManager,
    mocker: "MockerFixture",
):
    """Repeated requests should not restart B5DC communication."""
    mode = ControlMode.NO_MONITOR_NO_CONTROL

    component_manager.set_b5dc_control_mode(
        mode,
        sync=False,
    )

    b5dc_cm = component_manager.sub_component_managers["B5DC"]

    mock_stop = mocker.patch.object(
        b5dc_cm,
        "stop_communicating",
    )

    mock_start = mocker.patch.object(
        b5dc_cm,
        "start_communicating",
    )
    mock_sync = mocker.patch.object(
        component_manager,
        "sync_component_states",
    )
    mock_warning = mocker.patch.object(
        component_manager.logger,
        "warning",
    )
    component_manager.set_b5dc_control_mode(
        mode,
        sync=True,
    )
    mock_warning.assert_called_once_with(
        "B5DC is already in %s. No changes applied.",
        mode.name,
        extra=OPERATOR_TAG,
    )
    mock_stop.assert_not_called()
    mock_start.assert_not_called()
    mock_sync.assert_not_called()

    assert component_manager.check_device_control_mode("B5DC") == mode
