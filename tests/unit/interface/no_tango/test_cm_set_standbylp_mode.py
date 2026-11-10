"""Tests dish manager component manager setstandbylp command handler."""

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
    SPFRxOperatingMode,
)


@pytest.mark.unit
def test_set_standbylp_handler(
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
        target=component_manager.set_standby_lp_mode,
        args=(),
        kwargs={"task_callback": task_cb, "task_abort_event": task_abort_event},
        daemon=True,
    ).start()
    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values(timeout=1)

    component_manager.sub_component_managers["SPF"]._update_component_state(
        operatingmode=SPFOperatingMode.STANDBY_LP
    )
    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        operatingmode=SPFRxOperatingMode.STANDBY
    )
    component_manager.sub_component_managers["DS"]._update_component_state(
        operatingmode=DSOperatingMode.STANDBY, powerstate=DSPowerState.LOW_POWER
    )

    # check that the component state reports the requested command
    received_updates = component_state_cb.get_queue_values()
    last_update = received_updates[-1]
    assert last_update == {"dishmode": DishMode.STANDBY_LP}

    # check that the updates come through
    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=None, progress_info="Awaiting SPF operatingmode change to STANDBY_LP"),
        call(progress=None, progress_info="Awaiting SPFRX operatingmode change to STANDBY"),
        call(
            progress=None,
            progress_info="Awaiting DS operatingmode, powerstate change to STANDBY, LOW_POWER",
        ),
        call(
            progress=None,
            progress_info=(
                "Fanned out commands: SPF.SetStandbyLPMode, SPFRX.SetStandbyMode, "
                "DS.SetStandbyMode"
            ),
        ),
        call(progress=None, progress_info="Awaiting dishmode change to STANDBY_LP"),
        call(progress=None, progress_info="SPF operatingmode changed to STANDBY_LP"),
        call(progress=None, progress_info="SPF.SetStandbyLPMode completed"),
        call(progress=None, progress_info="SPFRX operatingmode changed to STANDBY"),
        call(progress=None, progress_info="SPFRX.SetStandbyMode completed"),
        call(progress=None, progress_info="DS operatingmode changed to STANDBY"),
        call(progress=None, progress_info="DS powerstate changed to LOW_POWER"),
        call(progress=None, progress_info="DS.SetStandbyMode completed"),
        call(progress=None, progress_info="SetStandbyLPMode completed."),
        call(status=TaskStatus.COMPLETED, result=(ResultCode.OK, "SetStandbyLPMode completed.")),
    ]
