"""
Abstracts all the logic for executing commands on the device server
"""

import logging
from functools import partial
from threading import Event
from typing import Any, Callable, Optional

from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.models.dish_enums import DishMode, PointingState, TrackTableLoadMode
from ska_mid_dish_manager.utils.ska_epoch_to_tai import get_current_tai_timestamp


class Abort:
    """Abort command handler"""

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
        self, task_callback: Optional[Callable] = None, task_abort_event: Optional[Event] = None
    ) -> None:
        self.abort(task_callback=task_callback, task_abort_event=task_abort_event)

    def _reset_track_table(self) -> None:
        """
        Write the last achievedPointing back to the trackTable in loadmode NEW

        NOTE: this is a workaround until the RESET mode is implemented on the DSC.
        Remove/re-work this when the RESET mode is available
        """
        current_pointing = self._component_manager.component_state.get("achievedpointing")
        timestamp = get_current_tai_timestamp()
        current_pointing[0] = timestamp
        sequence_length = 1
        load_mode = TrackTableLoadMode.NEW

        result_code, result_message = self._component_manager.track_load_table(
            sequence_length, current_pointing, load_mode
        )
        if result_code == ResultCode.OK:
            # need to find a way to bubble up this table
            # to dish manager._program_track_table and _load_mode
            pass
        else:
            self.logger.warning(
                "Failed to reset programTrackTable in Abort sequence: %s", result_message
            )

    def _ensure_transition_to_fp_mode(
        self,
        task_abort_event: Optional[Event] = None,
        task_callback: Optional[Callable] = None,
    ) -> None:
        # get fresh component states from the sub devices
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
        self._command_map.set_standby_fp_mode(task_abort_event, task_callback)

    def abort(
        self,
        task_callback: Optional[Callable] = None,
        task_abort_event: Optional[Event] = None,
    ) -> None:
        """Executes the abort sequence"""
        # the name has to be different, task_callback != task_cb
        # one is a partial with a command id and the other isnt
        task_cb = self._command_tracker.update_command_info

        if task_callback:
            task_callback(status=TaskStatus.IN_PROGRESS)

        if self._component_manager.is_lrc_currently_executing():
            self.logger.debug("Aborting LRCs from Abort sequence")
            abort_command_id = self._command_tracker.new_command(
                "abort-sequence:abort-lrc", completed_callback=None
            )
            abort_task_cb = partial(task_cb, abort_command_id)
            self._component_manager.abort_commands(task_callback=abort_task_cb)
            while (
                not self._command_tracker.get_command_status(abort_command_id)
                != TaskStatus.COMPLETED
            ):
                task_abort_event.wait(0.1)  # sleep a bit to not overwork the CPU

        # is the dish moving
        pointing_state = self._component_manager.component_state.get("pointingstate")
        if pointing_state in [PointingState.SLEW, PointingState.TRACK]:
            # stop the dish
            track_stop_command_id = self._command_tracker.new_command(
                "abort-sequence:trackstop", completed_callback=None
            )
            track_stop_task_cb = partial(task_cb, track_stop_command_id)
            self.logger.debug("Issuing TrackStop from Abort sequence")
            self._command_map.track_stop_cmd(task_abort_event, track_stop_task_cb)

            # clear the scan id
            end_scan_command_id = self._command_tracker.new_command(
                "abort-sequence:endscan", completed_callback=None
            )
            end_scan_task_cb = partial(task_cb, end_scan_command_id)
            self.logger.debug("Issuing EndScan from Abort sequence")
            # pylint: disable=protected-access
            self._component_manager._end_scan(task_abort_event, end_scan_task_cb)

        # send the last reported achieved pointing in load mode new
        self.logger.debug("Resetting the programTrackTable from Abort sequence")
        self._reset_track_table()

        # go to the known state: STANDBY-FP
        standby_fp_command_id = self._command_tracker.new_command(
            "abort-sequence:standbyfp", completed_callback=None
        )
        standby_fp_task_cb = partial(task_cb, standby_fp_command_id)
        self.logger.debug("Issuing SetStandbyFPMode from Abort sequence")
        self._ensure_transition_to_fp_mode(task_abort_event, standby_fp_task_cb)

        if task_callback:
            task_callback(
                status=TaskStatus.COMPLETED, result=(ResultCode.OK, "Abort sequence completed")
            )


# pylint: disable=too-few-public-methods
class SetStandbyLPMode:
    """SetStandbyLPMode command handler"""


class SetStandbyFPMode:
    """SetStandbyFPMode command handler"""


class SetOperateMode:
    """SetOperateMode command handler"""


class Track:
    """Track command handler"""


class TrackStop:
    """TrackStop command handler"""


class ConfigureBand:
    """ConfigureBand command handler"""


class SetStowMode:
    """SetStowMode command handler"""


class AnyOtherCommand:
    """_summary_"""
