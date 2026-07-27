"""Tests for the completion delay of a FannedOutCommand."""

import logging
from unittest import mock

import pytest
from ska_control_model import TaskStatus

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    FannedOutCommandStatus,
    SPFRxOperatingMode,
)
from ska_mid_dish_manager.models.fanned_out_command import FannedOutTangoCommand

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

DELAY_S = 5.0


@pytest.mark.unit
class TestCompletionDelay:
    """Tests for a command whose device reports its pre-command state for a while.

    Models SPFRx ConfigureBand, which is fanned out while SPFRx is already in OPERATE and only
    moves to CONFIGURE once it starts configuring.
    """

    # pylint: disable=protected-access,attribute-defined-outside-init
    def setup_method(self):
        """Set up a command whose awaited state is already satisfied when it is fanned out."""
        self.component_state = {
            "configuredband": Band.B2,
            "operatingmode": SPFRxOperatingMode.OPERATE,
        }
        self.device_component_manager = mock.MagicMock(
            _component_state=self.component_state,
            execute_command=mock.MagicMock(return_value=(TaskStatus.IN_PROGRESS, "command_id")),
        )

    def _build_command(self, **kwargs):
        """Build a fanned out command awaiting the state SPFRx is already in."""
        return FannedOutTangoCommand(
            logger=LOGGER,
            device="SPFRX",
            command_name="ConfigureBand2",
            device_component_manager=self.device_component_manager,
            awaited_component_state={
                "configuredband": Band.B2,
                "operatingmode": SPFRxOperatingMode.OPERATE,
            },
            timeout_s=30,
            **kwargs,
        )

    @pytest.mark.unit
    def test_does_not_complete_against_the_pre_command_state(self):
        """The command must not complete off the state the device was already in."""
        command = self._build_command(completion_delay_s=DELAY_S)

        command.execute(task_callback=None)
        command.report_progress(task_callback=None)

        assert command.status == FannedOutCommandStatus.IN_PROGRESS

    @pytest.mark.unit
    def test_completes_once_the_delay_has_elapsed(self):
        """Once the device's state can be trusted, the awaited state completes the command."""
        command = self._build_command(completion_delay_s=DELAY_S)
        command.execute(task_callback=None)

        command.start_time -= DELAY_S
        command.report_progress(task_callback=None)

        assert command.status == FannedOutCommandStatus.COMPLETED

    @pytest.mark.unit
    def test_keeps_waiting_after_the_delay_until_the_awaited_state_is_reached(self):
        """The delay only defers the awaited state check, it does not replace it."""
        command = self._build_command(completion_delay_s=DELAY_S)
        command.execute(task_callback=None)
        command.start_time -= DELAY_S

        self.component_state["operatingmode"] = SPFRxOperatingMode.CONFIGURE
        command.report_progress(task_callback=None)
        assert command.status == FannedOutCommandStatus.IN_PROGRESS

        self.component_state["operatingmode"] = SPFRxOperatingMode.OPERATE
        command.report_progress(task_callback=None)
        assert command.status == FannedOutCommandStatus.COMPLETED

    @pytest.mark.unit
    def test_completes_immediately_without_a_completion_delay(self):
        """Commands that do not set a completion delay are unaffected."""
        command = self._build_command()
        command.execute(task_callback=None)

        command.report_progress(task_callback=None)

        assert command.status == FannedOutCommandStatus.COMPLETED
