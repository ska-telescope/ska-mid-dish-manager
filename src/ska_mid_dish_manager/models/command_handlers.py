"""Abstracts all the logic for executing commands on the device."""

import logging
import time
from functools import partial
from threading import Event
from typing import Any, Callable, Optional

from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.models.dish_enums import DishMode, PointingState, TrackTableLoadMode


class Abort:
    """Abort command handler."""

    def __init__(
        self,
        component_manager: Any,
        command_map: Any,
        command_tracker: Any,
        logger: logging.Logger,
    ):
        self.logger = logger
        self._component_manager = component_manager
        self._command_map = command_map
        self._command_tracker = command_tracker

    def __call__(
        self,
        abort_command_id: str,
        task_abort_event: Event,
        task_callback: Optional[Callable] = None,
    ) -> None:
        self.abort(abort_command_id, task_abort_event, task_callback=task_callback)

    def _stop_dish_slew(self, task_abort_event: Event, task_callback: Optional[Callable] = None):
        if task_abort_event.is_set():
            self.logger.debug("abort-sequence: failed to stop dish slew")
            if task_callback:
                task_callback(status=TaskStatus.FAILED)
            return

        self.logger.debug("abort-sequence: stopping dish slew")
        try:
            self._command_map.track_stop_cmd(task_abort_event, task_callback)
            self.logger.debug("abort-sequence: dish slew has been successfully stopped")
        except Exception as exc:  # pylint:disable=broad-except
            if task_callback:
                task_callback(status=TaskStatus.FAILED, exception=exc)
            task_abort_event.set()
            self.logger.error("abort-sequence: failed to stop dish slew: %s", str(exc))

    def _wait_for_dish_to_settle(self, task_abort_event: Event) -> None:
        self.logger.debug("abort-sequence: waiting for the dish to settle")
        start_time = time.time()
        timeout = 30  # seconds
        while time.time() - start_time <= timeout:
            current_pointing_state = self._component_manager.component_state.get("pointingstate")
            if current_pointing_state == PointingState.READY:
                self.logger.debug(
                    "abort-sequence: dish has stopped moving "
                    "and is pointing close to the reset point"
                )
                break
            task_abort_event.wait(1.0)  # Avoid busy waiting
        else:
            task_abort_event.set()

    def _reset_track_table(self, task_abort_event: Event) -> None:
        """Writes the last achievedPointing back to the trackTable in loadmode NEW."""
        if task_abort_event.is_set():
            self.logger.debug("abort-sequence: failed to reset programTrackTable")
            return

        self.logger.debug("abort-sequence: resetting the programTrackTable")
        reset_point = self._component_manager.component_state.get("achievedpointing")
        # TODO: Verify how to properly reset the track table
        timestamp = (
            self._component_manager.get_current_tai_offset_from_dsc_with_manual_fallback() + 5
        )  # add 5 seconds lead time
        reset_point = [timestamp, reset_point[1], reset_point[2]]
        sequence_length = 1
        load_mode = TrackTableLoadMode.NEW

        result_code, result_message = self._component_manager.track_load_table(
            sequence_length, reset_point, load_mode
        )
        if result_code == ResultCode.OK:
            self._wait_for_dish_to_settle(task_abort_event)
            if task_abort_event.is_set():
                self.logger.debug(
                    "abort-sequence: timeout reached waiting for dish to settle at reset point %s",
                    reset_point,
                )
        else:
            task_abort_event.set()
            self.logger.debug(
                "abort-sequence: failed to reset programTrackTable with message: %s",
                result_message,
            )

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
            component_manager.update_state_from_monitored_attributes(task_abort_event)

        # only force the transition if the dish is not in FP already
        current_dish_mode = self._component_manager.component_state.get("dishmode")
        if current_dish_mode == DishMode.STANDBY_FP:
            if task_callback:
                task_callback(status=TaskStatus.COMPLETED)
            return

        # fan out respective FP command to the sub devices
        try:
            self._command_map.set_standby_fp_mode(task_abort_event, task_callback)
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

        if self._component_manager.is_dish_moving():
            pointing_state = self._component_manager.component_state.get("pointingstate")
            if pointing_state == PointingState.SLEW:
                track_stop_command_id = self._command_tracker.new_command(
                    "abort-sequence:trackstop", completed_callback=None
                )
                track_stop_task_cb = partial(task_cb, track_stop_command_id)
                self._stop_dish_slew(task_abort_event, track_stop_task_cb)
            else:
                # send the last reported achieved pointing in load mode new
                self._reset_track_table(task_abort_event)

            # clear the scan id
            end_scan_command_id = self._command_tracker.new_command(
                "abort-sequence:endscan", completed_callback=None
            )
            end_scan_task_cb = partial(task_cb, end_scan_command_id)
            self.logger.debug("abort-sequence: issuing EndScan")
            # pylint: disable=protected-access
            self._component_manager._end_scan(task_abort_event, end_scan_task_cb)

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
        abort_command_id: str,
        task_abort_event: Event,
        task_callback: Optional[Callable] = None,
    ) -> None:
        """Executes the abort sequence."""
        if abort_command_id is not None:
            while (
                self._command_tracker.get_command_status(abort_command_id) != TaskStatus.COMPLETED
            ):
                task_abort_event.wait(0.1)  # sleep a bit to not overwork the CPU

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
