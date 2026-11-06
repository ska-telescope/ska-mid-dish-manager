"""Abstracts all the logic for executing commands on the device."""

import logging
from threading import Event
from typing import Any, Callable, Optional

from ska_control_model import ResultCode, TaskStatus
from ska_tango_base.executor import TaskAborted

from ska_mid_dish_manager.models.command_actions import SetStandbyFPModeAction, TrackStopAction
from ska_mid_dish_manager.models.dish_enums import DishMode, PointingState
from ska_mid_dish_manager.utils.action_helpers import update_task_status


class AbortSequenceCommandHandler:
    """Abort command handler."""

    def __init__(self, component_manager: Any, logger: Optional[logging.Logger] = None) -> None:
        """Initialize the abort sequence command handler."""
        self._component_manager = component_manager
        self.logger = logger or component_manager.logger
        self.action_timeout_s = component_manager.get_action_timeout()
        self._abort_event = Event()

    def _reset_track_table(self, task_abort_event: Event) -> None:
        if task_abort_event.is_set():
            self.logger.error("abort-sequence: failed to reset track table")
            raise TaskAborted()

        self.logger.debug("abort-sequence: resetting track table")
        result_code, msg = self._component_manager.reset_track_table()
        if result_code == ResultCode.FAILED:
            self.logger.error(f"abort-sequence: ResetTrackTable failed: {msg}")
            raise RuntimeError(f"ResetTrackTable failed: {msg}")

        self.logger.debug("abort-sequence: track table has been successfully reset")

    def _stop_dish(self, task_abort_event: Event) -> None:
        if task_abort_event.is_set():
            self.logger.error("abort-sequence: failed to stop dish")
            raise TaskAborted()

        current_dish_mode = self._component_manager.component_state.get("dishmode")
        current_pointing_state = self._component_manager.component_state.get("pointingstate")
        if current_dish_mode == DishMode.STOW:
            self.logger.debug("abort-sequence: dish is in STOW mode, skipping track stop")
            return

        if current_pointing_state in (PointingState.READY, PointingState.UNKNOWN):
            self.logger.debug(
                "abort-sequence: dish is in [%s], skipping track stop", current_pointing_state
            )
            return

        self.logger.debug("abort-sequence: stopping dish")
        result_code, msg = TrackStopAction(
            self.logger, self._component_manager, self.action_timeout_s
        ).execute(task_abort_event)
        if result_code == ResultCode.FAILED:
            self.logger.error(f"TrackStop failed: {msg}")
            raise RuntimeError(f"TrackStop failed: {msg}")

        self.logger.debug("abort-sequence: dish has been successfully stopped")

    def _ensure_transition_to_fp_mode(self, task_abort_event: Event) -> None:
        if task_abort_event.is_set():
            self.logger.error("abort-sequence: failed to transition to StandbyFP mode")
            raise TaskAborted()

        self.logger.debug("abort-sequence: transitioning to StandbyFP dish mode")

        sub_component_mgrs = self._component_manager.get_active_sub_component_managers()
        for component_manager in sub_component_mgrs.values():
            component_manager.update_state_from_monitored_attributes()

        # only force the transition if the dish is not in FP already
        current_dish_mode = self._component_manager.component_state.get("dishmode")
        if current_dish_mode == DishMode.STANDBY_FP:
            return

        # fan out respective FP command to the sub devices
        result_code, msg = SetStandbyFPModeAction(
            self.logger, self._component_manager, self.action_timeout_s
        ).execute(task_abort_event)
        if result_code == ResultCode.FAILED:
            self.logger.error(f"SetStandbyFPMode failed: {msg}")
            raise RuntimeError(f"SetStandbyFPMode failed: {msg}")

        self.logger.debug("abort-sequence: SetStandbyFPMode command completed successfully")

    def complete_abort_sequence(
        self, task_abort_event: Optional[Event] = None, task_callback: Optional[Callable] = None
    ):
        self.logger.debug("Executing abort sequence")
        update_task_status(task_callback, status=TaskStatus.IN_PROGRESS)
        task_abort_event = task_abort_event or self._abort_event

        # the order the commands are run is important: so that the plc is not interrupted
        # mid way through a command. for e.g. dont call a lrc followed by a fast command
        # without any delay.
        # the sequence is as follows:
        # 1. TrackStop - lrc
        # 2. SetStandbyFPMode - lrc
        # 3. EndScan - fast command (nothing fanned out to sub devices)
        # 4. ResetTrackTable - fast command
        # The EndScan provides sufficient delay so that there is no contention when
        # ResetTrackTable is called after it - TODO: improvement chain commands on completion.

        try:
            # stop the dish
            self._stop_dish(task_abort_event)

            # go to STANDBY-FP
            self._ensure_transition_to_fp_mode(task_abort_event)

            # clear the scan id
            self.logger.debug("abort-sequence: issuing EndScan")
            self._component_manager.clear_scan_id_callback()

            # reset the track table
            self._reset_track_table(task_abort_event)
        except TaskAborted:
            update_task_status(
                task_callback,
                status=TaskStatus.FAILED,
                result=(ResultCode.FAILED, "Abort sequence failed"),
            )
        except RuntimeError as e:
            update_task_status(
                task_callback,
                status=TaskStatus.FAILED,
                result=(ResultCode.FAILED, f"Abort sequence failed: {str(e)}"),
            )
            return

        # report_task_progress("Abort sequence completed", self._progress_callback)
        update_task_status(
            task_callback,
            status=TaskStatus.COMPLETED,
            result=(ResultCode.OK, "Abort sequence completed"),
        )
        self.logger.debug("Abort sequence completed")
