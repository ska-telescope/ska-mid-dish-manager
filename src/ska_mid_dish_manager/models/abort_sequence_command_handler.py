"""Abstracts all the logic for executing commands on the device."""

import logging
from functools import partial
from threading import Event
from typing import Any, Callable, Optional

from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.models.command_actions import SetStandbyFPModeAction, TrackStopAction
from ska_mid_dish_manager.models.dish_enums import DishMode
from ska_mid_dish_manager.utils.helper_module import update_task_status


class Abort:
    """Abort command handler."""

    def __init__(self, component_manager: Any, command_tracker: Any, logger: logging.Logger):
        self.logger = logger
        self._component_manager = component_manager
        self._command_tracker = command_tracker

    def __call__(self, triggered_from_invoked: bool) -> None:
        if not triggered_from_invoked:
            command_id = self._command_tracker.new_command("Abort")
            task_callback = partial(self._command_tracker.update_command_info, command_id)
            self.abort(task_callback=task_callback)

    def _dummy_task_cb(self, *args, **kwargs):
        # TODO: remove after action handlers are updated to accept None for task callbacks
        pass

    def _reset_track_table(self, task_abort_event: Event) -> None:
        if task_abort_event.is_set():
            self.logger.debug("abort-sequence: failed to reset track table")
            return

        self.logger.debug("abort-sequence: resetting track table")
        result_code, msg = self._component_manager.reset_track_table()
        if result_code == ResultCode.FAILED:
            self.logger.error(f"abort-sequence: ResetTrackTable failed: {msg}")
            task_abort_event.set()
            return

        self.logger.debug("abort-sequence: track table has been successfully reset")

    def _stop_dish(self, task_abort_event: Event) -> None:
        if task_abort_event.is_set():
            self.logger.debug("abort-sequence: failed to stop dish")
            return

        self.logger.debug("abort-sequence: stopping dish")
        TrackStopAction(self.logger, self._component_manager).execute(
            self._dummy_task_cb, task_abort_event
        )
        self.logger.debug("abort-sequence: dish has been successfully stopped")

    def _ensure_transition_to_fp_mode(self, task_abort_event: Event) -> None:
        if task_abort_event.is_set():
            self.logger.debug("abort-sequence: failed to transition to StandbyFP mode")
            return

        self.logger.debug("abort-sequence: transitioning to StandbyFP dish mode")

        sub_component_mgrs = self._component_manager.get_active_sub_component_managers()
        for component_manager in sub_component_mgrs.values():
            component_manager.update_state_from_monitored_attributes()

        # only force the transition if the dish is not in FP already
        current_dish_mode = self._component_manager.component_state.get("dishmode")
        if current_dish_mode == DishMode.STANDBY_FP:
            return

        # fan out respective FP command to the sub devices
        SetStandbyFPModeAction(self.logger, self._component_manager).execute(
            self._dummy_task_cb, task_abort_event
        )
        self.logger.debug("abort-sequence: SetStandbyFPMode command completed successfully")

    def _complete_abort_sequence(
        self, task_abort_event: Event = Event(), task_callback: Optional[Callable] = None
    ):
        update_task_status(task_callback, status=TaskStatus.IN_PROGRESS)

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

        current_dish_mode = self._component_manager.component_state.get("dishmode")
        if current_dish_mode == DishMode.STOW:
            self.logger.debug("abort-sequence: dish is in STOW mode, skipping track stop")

        else:
            self._stop_dish(task_abort_event)

        # go to STANDBY-FP
        self._ensure_transition_to_fp_mode(task_abort_event)

        # clear the scan id
        self.logger.debug("abort-sequence: issuing EndScan")
        self._component_manager._end_scan(task_abort_event)

        # reset the track table
        self._reset_track_table(task_abort_event)

        if task_abort_event.is_set():
            self.logger.debug("Abort sequence failed")
            update_task_status(
                task_callback,
                status=TaskStatus.FAILED,
                progress="Abort sequence failed",
                result=(ResultCode.FAILED, "Abort sequence failed"),
            )
            return

        update_task_status(
            task_callback,
            status=TaskStatus.COMPLETED,
            progress="Abort sequence completed",
            result=(ResultCode.OK, "Abort sequence completed"),
        )
        self.logger.debug("Abort sequence completed")

    def abort(self, task_callback: Optional[Callable] = None) -> None:
        """Executes the abort sequence."""
        self._component_manager.submit_task(
            self._complete_abort_sequence,
            args=[],
            task_callback=task_callback,
        )
