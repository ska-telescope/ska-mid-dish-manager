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

    threading.Thread(
        target=component_manager.set_standby_fp_mode,
        args=(),
        kwargs={"task_callback": task_cb, "task_abort_event": task_abort_event},
        daemon=True,
    ).start()
    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values(timeout=1)

    component_manager.sub_component_managers["DS"]._update_component_state(
        operatingmode=DSOperatingMode.STANDBY, powerstate=DSPowerState.FULL_POWER
    )
    component_manager.sub_component_managers["SPF"]._update_component_state(
        operatingmode=SPFOperatingMode.OPERATE
    )

    # check that the component state reports the requested command
    received_updates = component_state_cb.get_queue_values()
    last_update = received_updates[-1]
    assert last_update == {"dishmode": DishMode.STANDBY_FP}

    # check that the updates come through
    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=None, progress_info="Awaiting DS operatingmode change to STANDBY"),
        call(progress=None, progress_info="Awaiting DS powerstate change to FULL_POWER"),
        call(progress=None, progress_info="Awaiting SPF operatingmode change to OPERATE"),
        call(
            progress=None,
            progress_info=(
                "Fanned out commands: DS.SetStandbyMode, DS.SetPowerMode, SPF.SetOperateMode"
            ),
        ),
        call(progress=None, progress_info="Awaiting dishmode change to STANDBY_FP"),
        call(progress=None, progress_info="DS operatingmode changed to STANDBY"),
        call(progress=None, progress_info="DS.SetStandbyMode completed"),
        call(progress=None, progress_info="DS powerstate changed to FULL_POWER"),
        call(progress=None, progress_info="DS.SetPowerMode completed"),
        call(progress=None, progress_info="SPF operatingmode changed to OPERATE"),
        call(progress=None, progress_info="SPF.SetOperateMode completed"),
        call(progress=None, progress_info="SetStandbyFPMode completed."),
        call(status=TaskStatus.COMPLETED, result=(ResultCode.OK, "SetStandbyFPMode completed.")),
    ]
