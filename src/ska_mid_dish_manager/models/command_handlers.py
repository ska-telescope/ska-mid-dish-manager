"""Abstracts all the logic for executing commands on the device."""

import logging
from functools import partial
from threading import Event
from typing import Any, Callable, Optional

from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.models.command_actions import SetStandbyFPModeAction, TrackStopAction
from ska_mid_dish_manager.models.dish_enums import DishMode


class Abort:
    """Abort command handler."""

    def __init__(
        self,
        component_manager: Any,
        command_tracker: Any,
        logger: logging.Logger,
    ):
        self.logger = logger
        self._component_manager = component_manager
        self._command_tracker = command_tracker

    def __call__(
        self,
        task_callback: Optional[Callable] = None,
    ) -> None:
        self.abort(task_callback=task_callback)

    def _stop_dish(self, task_abort_event: Event, task_callback: Optional[Callable] = None):
        if task_abort_event.is_set():
            self.logger.debug("abort-sequence: failed to stop dish")
            if task_callback:
                task_callback(status=TaskStatus.FAILED)
            return
        self.logger.debug("abort-sequence: stopping dish")
        try:
            TrackStopAction(self.logger, self._component_manager).execute(
                task_callback, task_abort_event
            )
            self.logger.debug("abort-sequence: dish slew has been successfully stopped")
        except Exception as exc:  # pylint:disable=broad-except
            if task_callback:
                task_callback(status=TaskStatus.FAILED, exception=exc)
            task_abort_event.set()
            self.logger.error("abort-sequence: failed to stop dish: %s", str(exc))

    def _ensure_transition_to_fp_mode(
        self,
        task_abort_event: Event,
        task_callback: Optional[Callable] = None,
    ) -> None:
        if task_abort_event.is_set():
            self.logger.debug("abort-sequence: failed to transition to StandbyFP mode")
            if task_callback:
                task_callback(status=TaskStatus.FAILED)
            return

        self.logger.debug("abort-sequence: transitioning to StandbyFP dish mode")

        sub_component_mgrs = self._component_manager.get_active_sub_component_managers()
        for component_manager in sub_component_mgrs.values():
            component_manager.update_state_from_monitored_attributes()

        # only force the transition if the dish is not in FP already
        current_dish_mode = self._component_manager.component_state.get("dishmode")
        if current_dish_mode == DishMode.STANDBY_FP:
            if task_callback:
                task_callback(status=TaskStatus.COMPLETED)
            return

        # fan out respective FP command to the sub devices
        try:
            SetStandbyFPModeAction(self.logger, self._component_manager).execute(
                task_callback, task_abort_event
            )
            self.logger.debug("abort-sequence: SetStandbyFPMode command completed successfully")
        except Exception as exc:  # pylint:disable=broad-except
            if task_callback:
                task_callback(status=TaskStatus.FAILED, exception=exc)
            task_abort_event.set()
            self.logger.error(
                "abort-sequence: failed to transition dish to StandbyFP mode: %s", str(exc)
            )

    def _complete_abort_sequence(
        self, task_abort_event: Optional[Event] = None, task_callback: Optional[Callable] = None
    ):
        if task_callback:
            task_callback(status=TaskStatus.IN_PROGRESS)

        # task_callback != task_cb, one is a partial with a command id and the other isnt
        task_cb = self._command_tracker.update_command_info

        track_stop_command_id = self._command_tracker.new_command(
            "abort-sequence:trackstop", completed_callback=None
        )
        track_stop_task_cb = partial(task_cb, track_stop_command_id)
        self._stop_dish(task_abort_event, track_stop_task_cb)

        # clear the scan id
        end_scan_command_id = self._command_tracker.new_command(
            "abort-sequence:endscan", completed_callback=None
        )
        end_scan_task_cb = partial(task_cb, end_scan_command_id)
        self.logger.debug("abort-sequence: issuing EndScan")
        self._component_manager._end_scan(task_abort_event, end_scan_task_cb)

        # reset the track table
        self._component_manager.reset_track_table()
        # go to STANDBY-FP
        standby_fp_command_id = self._command_tracker.new_command(
            "abort-sequence:standbyfp", completed_callback=None
        )
        standby_fp_task_cb = partial(task_cb, standby_fp_command_id)
        self._ensure_transition_to_fp_mode(task_abort_event, standby_fp_task_cb)

        if task_abort_event.is_set():
            self.logger.debug("Abort sequence failed")
            if task_callback:
                task_callback(
                    status=TaskStatus.FAILED,
                    result=(ResultCode.FAILED, "Abort sequence failed"),
                )
            return

        if task_callback:
            task_callback(
                status=TaskStatus.COMPLETED, result=(ResultCode.OK, "Abort sequence completed")
            )
        self.logger.debug("Abort sequence completed")

    def abort(
        self,
        task_callback: Optional[Callable] = None,
    ) -> None:
        """Executes the abort sequence."""
        self.logger.debug(
            "Handing over work from abort-thread to executor to complete the abort sequence"
        )
        self._component_manager.submit_task(
            self._complete_abort_sequence,
            args=[],
            task_callback=task_callback,
        )


class SetStandbyLPMode:
    """SetStandbyLPMode command handler."""


class SetStandbyFPMode:
    """SetStandbyFPMode command handler."""


class SetOperateMode:
    """SetOperateMode command handler."""


class Track:
    """Track command handler."""


class TrackStop:
    """TrackStop command handler."""


class ConfigureBand:
    """ConfigureBand command handler."""


class SetStowMode:
    """SetStowMode command handler."""


class AnyOtherCommand:
    """_summary_."""
