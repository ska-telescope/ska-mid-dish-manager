"""Tests dish manager component manager setstandbyfp command handler."""

import threading
from unittest.mock import MagicMock, call

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    DSPowerState,
    SPFOperatingMode,
)
from tests.utils import progress_call


@pytest.mark.unit
def test_set_standbyfp_handler(
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
    task_abort_event: threading.Event,
) -> None:
    """Verify behaviour of SetStandbyLP command handler.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks
    :param task_abort_event: the threading event used to signal task abortion
    """
    component_state_cb = callbacks["comp_state_cb"]
    task_cb = callbacks["task_cb"]
    ds_cm = component_manager.sub_component_managers["DS"]
    spf_cm = component_manager.sub_component_managers["SPF"]

    command_thread = threading.Thread(
        target=component_manager.set_standby_fp_mode,
        args=(),
        kwargs={"task_callback": task_cb, "task_abort_event": task_abort_event},
        daemon=True,
    )
    command_thread.start()

    ds_cm._update_component_state(
        operatingmode=DSOperatingMode.STANDBY, powerstate=DSPowerState.FULL_POWER
    )
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)

    # check that the component state reports the requested command
    component_state_cb.wait_for_value("dishmode", DishMode.STANDBY_FP)

    # wait for all the updates to be processed by the command thread
    command_thread.join(timeout=30)
    assert not command_thread.is_alive(), "SetStandbyFPMode did not finish in time"
    # check that the updates come through
    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        progress_call("SetStandbyFPMode started"),
        progress_call("DS.SetStandbyMode started"),
        progress_call("Awaiting DS operatingmode change to STANDBY"),
        progress_call("DS.SetPowerMode started"),
        progress_call("Awaiting DS powerstate change to FULL_POWER"),
        progress_call("SPF.SetOperateMode started"),
        progress_call("Awaiting SPF operatingmode change to OPERATE"),
        progress_call(
            "Fanned out commands: DS.SetStandbyMode, DS.SetPowerMode, SPF.SetOperateMode"
        ),
        progress_call("Awaiting dishmode change to STANDBY_FP"),
        progress_call("DS operatingmode changed to STANDBY"),
        progress_call("DS.SetStandbyMode completed"),
        progress_call("DS powerstate changed to FULL_POWER"),
        progress_call("DS.SetPowerMode completed"),
        progress_call("SPF operatingmode changed to OPERATE"),
        progress_call("SPF.SetOperateMode completed"),
        progress_call("SetStandbyFPMode completed."),
        call(status=TaskStatus.COMPLETED, result=(ResultCode.OK, "SetStandbyFPMode completed.")),
    ]
