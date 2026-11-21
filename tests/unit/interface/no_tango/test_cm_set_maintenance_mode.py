"""Tests dish manager component manager set_maintenance_mode command handler."""

import logging
import threading
from unittest.mock import MagicMock, call

import pytest
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DscCmdAuthType,
    DscCtrlState,
    DSOperatingMode,
    SPFOperatingMode,
    SPFRxOperatingMode,
)
from tests.utils import progress_call


@pytest.mark.unit
def test_set_maintenance_mode_handler(
    caplog,
    component_manager: DishManagerComponentManager,
    callbacks: dict[str, MagicMock],
    task_abort_event: threading.Event,
) -> None:
    """Verify behaviour of SetMaintenanceMode command handler.

    :param component_manager: the component manager under test
    :param callbacks: a dictionary of mocks
    :param task_abort_event: the threading event used to signal task abortion
    """
    component_state_cb = callbacks["comp_state_cb"]
    task_cb = callbacks["task_cb"]
    spfrx_cm = component_manager.sub_component_managers["SPFRX"]
    ds_cm = component_manager.sub_component_managers["DS"]
    spf_cm = component_manager.sub_component_managers["SPF"]

    caplog.set_level(logging.DEBUG)

    command_thread = threading.Thread(
        target=component_manager.set_maintenance_mode,
        args=(),
        kwargs={"task_callback": task_cb, "task_abort_event": task_abort_event},
        daemon=True,
    )
    command_thread.start()

    ds_cm._update_component_state(operatingmode=DSOperatingMode.STOW)
    component_state_cb.wait_for_value("dishmode", DishMode.STOW)
    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.STANDBY)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.MAINTENANCE)

    # finish the final bit of the maint transition
    ds_cm._update_component_state(
        dsccmdauth=DscCmdAuthType.NO_AUTHORITY,
        dscctrlstate=DscCtrlState.NO_AUTHORITY,
    )

    # check that the component state reports the requested command
    component_state_cb.wait_for_value("dishmode", DishMode.MAINTENANCE)

    # TODO: Remove below. Waiting for SPFRx to implement maintenance mode
    assert "Nothing done on SPFRx, awaiting implementation on it." in caplog.text

    # wait for all the updates to be processed by the command thread
    command_thread.join(timeout=30)
    assert not command_thread.is_alive(), "SetStandbyLPMode did not finish in time"
    # check that the updates come through
    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        progress_call("SetMaintenanceMode started"),
        progress_call("DS.Stow started"),
        progress_call("Awaiting DS operatingmode change to STOW"),
        progress_call("SPFRX.SetStandbyMode started"),
        progress_call("Awaiting SPFRX operatingmode change to STANDBY"),
        progress_call("SPF.SetMaintenanceMode started"),
        progress_call("Awaiting SPF operatingmode change to MAINTENANCE"),
        progress_call(
            "Fanned out commands: DS.Stow, SPFRX.SetStandbyMode, SPF.SetMaintenanceMode"
        ),
        progress_call("Awaiting dishmode change to STOW"),
        progress_call("DS operatingmode changed to STOW"),
        progress_call("DS.Stow completed"),
        progress_call("SPFRX operatingmode changed to STANDBY"),
        progress_call("SPFRX.SetStandbyMode completed"),
        progress_call("SPF operatingmode changed to MAINTENANCE"),
        progress_call("SPF.SetMaintenanceMode completed"),
        progress_call("SetMaintenanceMode complete. Triggering on success action."),
        progress_call("ReleaseAuth started"),
        progress_call("DS.ReleaseAuth started"),
        progress_call("Awaiting DS dsccmdauth, dscctrlstate change to NO_AUTHORITY, NO_AUTHORITY"),
        progress_call("Fanned out commands: DS.ReleaseAuth"),
        progress_call("Awaiting dsccmdauth, dscctrlstate change to NO_AUTHORITY, NO_AUTHORITY"),
        progress_call("DS dsccmdauth changed to NO_AUTHORITY"),
        progress_call("DS dscctrlstate changed to NO_AUTHORITY"),
        progress_call("DS.ReleaseAuth completed"),
        progress_call("SetMaintenanceMode completed."),
        call(status=TaskStatus.COMPLETED, result=(ResultCode.OK, "SetMaintenanceMode completed.")),
    ]
