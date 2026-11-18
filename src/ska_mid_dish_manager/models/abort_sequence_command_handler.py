"""Abstracts all the logic for executing commands on the device."""

import logging
from threading import Event
from typing import Any, Callable, Optional

from ska_control_model import ResultCode, TaskStatus
from ska_tango_base.executor import TaskAborted

from ska_mid_dish_manager.models.command_actions import (
    SetStandbyFPModeAction,
    TrackStopAction,
)
from ska_mid_dish_manager.models.dish_enums import DishMode, PointingState
from ska_mid_dish_manager.utils.action_helpers import update_task_status


class AbortSequenceCommandHandler:
    """Abort command handler."""

    def __init__(self, component_manager: Any, logger: Optional[logging.Logger] = None) -> None:
        """Initialize the abort sequence command handler."""
        self._component_manager = component_manager
        self.logger = logger or component_manager.logger
        self.action_timeout_s = component_manager.get_action_timeout()

    def _stop_dish(self, task_abort_event: Event) -> None:
        if task_abort_event.is_set():
            self.logger.info("abort-sequence: cancelled before stopping the dish")
            raise TaskAborted()

        current_dish_mode = self._component_manager.component_state.get("dishmode")
        current_pointing_state = self._component_manager.component_state.get("pointingstate")
        if current_dish_mode == DishMode.STOW:
            self.logger.debug("abort-sequence: dish is in STOW mode, skipping track stop")
            return

        if current_pointing_state in (PointingState.READY, PointingState.UNKNOWN):
            self.logger.debug(
                "abort-sequence: dish is in pointing state %s, skipping track stop",
                current_pointing_state.name,
            )
            return

        self.logger.debug("abort-sequence: stopping dish")
        result_code, msg = TrackStopAction(
            self.logger, self._component_manager, self.action_timeout_s
        ).execute(task_abort_event)
        if result_code == ResultCode.FAILED:
            raise RuntimeError(f"TrackStop failed: {msg}")

        self.logger.debug("abort-sequence: dish has been successfully stopped")

    def _ensure_transition_to_fp_mode(self, task_abort_event: Event) -> None:
        if task_abort_event.is_set():
            self.logger.info("abort-sequence: cancelled before transitioning to STANDBY_FP")
            raise TaskAborted()

        # leave a stowed dish in STOW, and don't repeat the transition if it's already done
        current_dish_mode = self._component_manager.component_state.get("dishmode")
        if current_dish_mode in (DishMode.STOW, DishMode.STANDBY_FP):
            self.logger.debug(
                "abort-sequence: dish is in %s, skipping transition to STANDBY_FP",
                DishMode(current_dish_mode).name,
            )
            return

        self.logger.debug("abort-sequence: transitioning to STANDBY_FP")
        result_code, msg = SetStandbyFPModeAction(
            self.logger, self._component_manager, self.action_timeout_s
        ).execute(task_abort_event)
        if result_code == ResultCode.FAILED:
            raise RuntimeError(f"SetStandbyFPMode failed: {msg}")

        self.logger.debug("abort-sequence: transitioned to STANDBY_FP")

    def _reset_track_table(self, task_abort_event: Event) -> None:
        if task_abort_event.is_set():
            self.logger.info("abort-sequence: cancelled before resetting the track table")
            raise TaskAborted()

        self.logger.debug("abort-sequence: resetting track table")
        result_code, msg = self._component_manager.reset_track_table()
        if result_code == ResultCode.FAILED:
            raise RuntimeError(f"ResetTrackTable failed: {msg}")

        self.logger.debug("abort-sequence: track table has been successfully reset")

    def complete_abort_sequence(self, task_abort_event: Event, task_callback: Callable) -> None:
        """Stop the dish, go to STANDBY_FP, clear the scan ID and reset the track table.

        :param task_abort_event: Event used to signal that the task should be aborted.
        :type task_abort_event: threading.Event
        :param task_callback: Callback used to report the status of the task.
        :type task_callback: Callable
        """
        try:
            self.logger.debug("Executing abort sequence")
            update_task_status(task_callback, status=TaskStatus.IN_PROGRESS)
            # The order matters, so the PLC isn't interrupted part way through a command,
            # for example by a fast command straight after a long running command:
            # 1. TrackStop - long running command
            # 2. SetStandbyFPMode - long running command
            # 3. EndScan - local, nothing fanned out to sub-devices
            # 4. ResetTrackTable - fast command
            self._stop_dish(task_abort_event)
            self._ensure_transition_to_fp_mode(task_abort_event)
            self.logger.debug("abort-sequence: issuing EndScan")
            self._component_manager.clear_scan_id_callback()
            self._reset_track_table(task_abort_event)
        except TaskAborted:
            update_task_status(
                task_callback,
                status=TaskStatus.ABORTED,
                result=(ResultCode.ABORTED, "Abort sequence cancelled"),
            )
        except Exception as e:
            # Any failure must still end the task, so the Abort command doesn't hang
            self.logger.exception("Abort sequence failed")
            update_task_status(
                task_callback,
                status=TaskStatus.FAILED,
                result=(ResultCode.FAILED, f"Abort sequence failed: {e}"),
            )
        else:
            update_task_status(
                task_callback,
                status=TaskStatus.COMPLETED,
                result=(ResultCode.OK, "Abort sequence completed"),
            )
            self.logger.debug("Abort sequence completed")
