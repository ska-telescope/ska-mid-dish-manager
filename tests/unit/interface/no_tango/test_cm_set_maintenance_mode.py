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

    caplog.set_level(logging.DEBUG)

    threading.Thread(
        target=component_manager.set_maintenance_mode,
        args=(),
        kwargs={"task_callback": task_cb, "task_abort_event": task_abort_event},
        daemon=True,
    ).start()
    # wait a bit for the lrc updates to come through
    component_state_cb.get_queue_values(timeout=1)

    component_manager.sub_component_managers["SPFRX"]._update_component_state(
        operatingmode=SPFRxOperatingMode.STANDBY
    )
    component_manager.sub_component_managers["SPF"]._update_component_state(
        operatingmode=SPFOperatingMode.MAINTENANCE
    )
    component_manager.sub_component_managers["DS"]._update_component_state(
        operatingmode=DSOperatingMode.STOW
    )
    component_state_cb.wait_for_value("dishmode", DishMode.STOW)

    # finish the final bit of the maint transition
    component_manager.sub_component_managers["DS"]._update_component_state(
        dsccmdauth=DscCmdAuthType.NO_AUTHORITY,
        dscctrlstate=DscCtrlState.NO_AUTHORITY,
    )

    # check that the component state reports the requested command
    component_state_cb.wait_for_value("dishmode", DishMode.MAINTENANCE)

    # TODO: Remove below. Waiting for SPFRx to implement maintenance mode
    assert "Nothing done on SPFRx, awaiting implementation on it." in caplog.text

    assert task_cb.call_args_list == [
        call(status=TaskStatus.IN_PROGRESS),
        call(progress=None, progress_info="Awaiting DS operatingmode change to STOW"),
        call(progress=None, progress_info="Awaiting SPFRX operatingmode change to STANDBY"),
        call(progress=None, progress_info="Awaiting SPF operatingmode change to MAINTENANCE"),
        call(
            progress=None,
            progress_info=(
                "Fanned out commands: DS.Stow, SPFRX.SetStandbyMode, SPF.SetMaintenanceMode"
            ),
        ),
        call(progress=None, progress_info="Awaiting dishmode change to STOW"),
        call(progress=None, progress_info="DS operatingmode changed to STOW"),
        call(progress=None, progress_info="DS.Stow completed"),
        call(progress=None, progress_info="SPFRX operatingmode changed to STANDBY"),
        call(progress=None, progress_info="SPFRX.SetStandbyMode completed"),
        call(progress=None, progress_info="SPF operatingmode changed to MAINTENANCE"),
        call(progress=None, progress_info="SPF.SetMaintenanceMode completed"),
        call(
            progress=None,
            progress_info="SetMaintenanceMode complete. Triggering on success action.",
        ),
        call(
            progress=None,
            progress_info=(
                "Awaiting DS dsccmdauth, dscctrlstate change to NO_AUTHORITY, NO_AUTHORITY"
            ),
        ),
        call(progress=None, progress_info="Fanned out commands: DS.ReleaseAuth"),
        call(
            progress=None,
            progress_info="Awaiting dsccmdauth, dscctrlstate change to NO_AUTHORITY, NO_AUTHORITY",
        ),
        call(progress=None, progress_info="DS dsccmdauth changed to NO_AUTHORITY"),
        call(progress=None, progress_info="DS dscctrlstate changed to NO_AUTHORITY"),
        call(progress=None, progress_info="DS.ReleaseAuth completed"),
        call(status=TaskStatus.COMPLETED, result=(ResultCode.OK, "SetMaintenanceMode completed.")),
    ]
