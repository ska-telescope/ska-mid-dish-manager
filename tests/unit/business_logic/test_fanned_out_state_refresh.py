"""Tests the component state refresh of fanned out tango commands."""

import logging
from unittest.mock import MagicMock

import pytest
from ska_control_model import TaskStatus

from ska_mid_dish_manager.models.dish_enums import FannedOutCommandStatus
from ska_mid_dish_manager.models.fanned_out_command import FannedOutTangoCommand

LOGGER = logging.getLogger(__name__)


def _command(awaited_component_state=None, is_device_ignored=False) -> FannedOutTangoCommand:
    device_cm = MagicMock()
    device_cm._component_state = {"operatingmode": "STANDBY"}
    device_cm.execute_command.return_value = (TaskStatus.IN_PROGRESS, "started")
    if awaited_component_state is None:
        awaited_component_state = {"operatingmode": "OPERATE"}
    return FannedOutTangoCommand(
        logger=LOGGER,
        device="DS",
        command_name="SetPointMode",
        device_component_manager=device_cm,
        awaited_component_state=awaited_component_state,
        timeout_s=0,
        is_device_ignored=is_device_ignored,
    )


@pytest.mark.unit
def test_refresh_runs_on_every_progress_check():
    command = _command()
    refresh = command.device_component_manager.update_state_from_monitored_attributes
    command.execute()

    command.report_progress()
    refresh.assert_called_once_with(("operatingmode",))

    command.report_progress()
    assert refresh.call_count == 2


@pytest.mark.unit
def test_refreshed_state_completes_the_command():
    command = _command()
    device_cm = command.device_component_manager
    device_cm.update_state_from_monitored_attributes.side_effect = lambda _: (
        device_cm._component_state.update(operatingmode="OPERATE")
    )
    command.execute()

    command.report_progress()

    assert command.status == FannedOutCommandStatus.COMPLETED


@pytest.mark.unit
def test_no_refresh_once_finished():
    command = _command()
    refresh = command.device_component_manager.update_state_from_monitored_attributes
    command.execute()
    command.device_component_manager._component_state["operatingmode"] = "OPERATE"
    command.report_progress()
    assert command.status == FannedOutCommandStatus.COMPLETED
    refresh.reset_mock()

    command.report_progress()

    refresh.assert_not_called()


@pytest.mark.unit
def test_no_refresh_for_ignored_device():
    command = _command(is_device_ignored=True)
    refresh = command.device_component_manager.update_state_from_monitored_attributes
    command.execute()

    command.report_progress()

    assert command.status == FannedOutCommandStatus.IGNORED
    refresh.assert_not_called()


@pytest.mark.unit
def test_refresh_without_awaited_state_does_not_read_all_attributes():
    command = _command(awaited_component_state={})

    command.refresh_state_from_device()

    command.device_component_manager.update_state_from_monitored_attributes.assert_not_called()


@pytest.mark.unit
def test_failed_refresh_does_not_stop_the_command(caplog):
    command = _command()
    refresh = command.device_component_manager.update_state_from_monitored_attributes
    refresh.side_effect = RuntimeError("Connection interrupted")
    command.execute()

    with caplog.at_level(logging.ERROR):
        command.report_progress()

    assert command.status == FannedOutCommandStatus.IN_PROGRESS
    assert "Failed to refresh the component state" in caplog.text

    # retried on the next check
    command.report_progress()
    assert refresh.call_count == 2
