"""Module containing the fanned out command actions."""

import json
import logging
import time
from abc import ABC
from typing import Any, Callable, List, Optional

import tango
from ska_control_model import AdminMode, ResultCode, TaskStatus

from ska_mid_dish_manager.models.constants import DEFAULT_ACTION_TIMEOUT_S, DSC_MIN_POWER_LIMIT_KW
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
    DSOperatingMode,
    DSPowerState,
    IndexerPosition,
    PointingState,
    SPFOperatingMode,
    SPFRxOperatingMode,
)
from ska_mid_dish_manager.models.fanned_out_command import FannedOutCommand, FannedOutSlowCommand
from ska_mid_dish_manager.utils.action_helpers import (
    check_component_state_matches_awaited,
    report_awaited_attributes,
    report_task_progress,
    update_task_status,
)


class Action(ABC):
    """Base class for actions.

    The ``Action`` class represents a high-level operation that involves executing one or more
    commands on subservient devices. Each concrete subclass is responsible for defining its own
    :class:`FannedOutSlowCommand` instances and assigning an :class:`ActionHandler` instance
    to coordinate and monitor their execution.

    Actions can be chained using optional ``action_on_success`` and ``action_on_failure``
    callbacks, allowing for conditional execution sequences.
    """

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        timeout_s: float = DEFAULT_ACTION_TIMEOUT_S,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        """:param logger: Logger instance.
        :type logger: logging.Logger
        :param dish_manager_cm: The DishManagerComponentManager instance.
        :type dish_manager_cm: DishManagerComponentManager
        :param timeout_s: Timeout (in seconds) for this action to complete. Defaults to
            DEFAULT_ACTION_TIMEOUT_S.
        :type timeout_s: float
        :param action_on_success: Optional Action to execute automatically if this action succeeds.
        :type action_on_success: Optional[Action]
        :param action_on_failure: Optional Action to execute automatically if this action fails.
        :type action_on_failure: Optional[Action]
        :param waiting_callback: Optional callback executed periodically while waiting on commands.
        :type waiting_callback: Optional[Callable]
        """
        self.logger = logger
        self.dish_manager_cm = dish_manager_cm
        self.action_on_success = action_on_success
        self.action_on_failure = action_on_failure
        self.waiting_callback = waiting_callback
        self.timeout_s = timeout_s
        self._handler: Optional["ActionHandler"] = None
        self._progress_callback = dish_manager_cm._command_progress_callback

    @property
    def handler(self) -> "ActionHandler":
        """:return: The ActionHandler instance assigned to this action.
        :rtype: ActionHandler
        :raises NotImplementedError: If no handler has been assigned by the subclass.
        """
        if self._handler is None:
            raise NotImplementedError("Action does not have a handler")
        return self._handler

    def execute(
        self, task_callback: Callable, task_abort_event: Any, completed_response_msg: str = ""
    ):
        """Execute the defined action using the assigned handler.

        :param task_callback: Callback function used for reporting.
        :type task_callback: Callable
        :param task_abort_event: Event or flag used to signal that the task should be aborted.
        :type task_abort_event: Any
        :param completed_response_msg: Optional message to use upon successful completion.
        :type completed_response_msg: str
        :raises NotImplementedError: If the action has no assigned handler.
        """
        self.handler.execute(task_callback, task_abort_event, completed_response_msg)


class ActionHandler:
    """Manages a group of fanned-out commands. It succeeds only if all fanned-out commands complete
    successfully. It fails if any fanned out command fails or times out, or if the main action
    times out.
    """

    def __init__(
        self,
        logger: logging.Logger,
        action_name: str,
        fanned_out_commands: List[FannedOutCommand],
        component_state: dict,
        awaited_component_state: Optional[dict] = {},
        action_on_success: Optional[Action] = None,
        action_on_failure: Optional[Action] = None,
        waiting_callback: Optional[Callable] = None,
        progress_callback: Optional[Callable] = None,
        timeout_s: float = DEFAULT_ACTION_TIMEOUT_S,
    ):
        """:param logger: Logger instance
        :type logger: Logger
        :param action_name: A name for this command action
        :type action_name: str
        :param fanned_out_commands: A list of FannedOutCommand classes to be executed.
        :type fanned_out_commands: list[FannedOutCommand]
        :param component_state: The component state containing the attributes to wait for updates
            on.
        :type component_state: Optional[dict]
        :param awaited_component_state: The component state containing the attributes and values to
            wait for.
        :type awaited_component_state: Optional[dict]
        :param action_on_success: Optional Action to execute on success.
        :type action_on_success: Callable
        :param action_on_success: Optional Action to execute on failure.
        :type action_on_failure: Callable[str]
        :param waiting_callback: Optional callback to execute on each iteration while waiting on
            commands.
        :type waiting_callback: Callable[str]
        :param progress_callback: Optional callback to report progress updates.
        :type progress_callback: Callable
        :param timeout_s: Timeout (in seconds) for the action to complete.
        :type timeout_s: float
        """
        self.logger = logger
        self.action_name = action_name
        self.fanned_out_commands = fanned_out_commands
        self.component_state = component_state
        self.awaited_component_state = awaited_component_state
        self.action_on_success: Optional[Action] = action_on_success
        self.action_on_failure: Optional[Action] = action_on_failure
        self.waiting_callback = waiting_callback
        self.progress_callback = progress_callback
        self.timeout_s = timeout_s or self._compute_timeout()

    def _compute_timeout(self) -> float:
        """Compute the timeout for the action based on the fanned out command timeouts.

        :return: The timeout value in seconds.
        :rtype: float
        """
        max_timeout = max((c.timeout_s for c in self.fanned_out_commands), default=0)
        return max_timeout + 5 if max_timeout > 0 else 0

    def _trigger_failure(
        self,
        task_callback,
        task_abort_event,
        message: str,
        task_status=TaskStatus.FAILED,
        result_code=ResultCode.FAILED,
    ) -> None:
        """Handle failure of the action and optionally trigger the on-failure action.

        :param task_callback: Callback function used for reporting.
        :type task_callback: Callable
        :param task_abort_event: Event or flag used to signal task abortion.
        :type task_abort_event: Any
        :param message: Failure message.
        :type message: str
        :param task_status: Status to use for the task_callback (default: TaskStatus.FAILED).
        :type task_status: TaskStatus
        :param result_code: Result code to use for the task_callback (default: ResultCode.FAILED).
        :type result_code: ResultCode
        """
        self.logger.error(message)
        report_task_progress(message, self.progress_callback)

        if self.action_on_failure:
            next_action_msg = f"{self.action_name} failed. Triggering on failure action."
            self.logger.debug(next_action_msg)
            report_task_progress(next_action_msg, self.progress_callback)
            self.action_on_failure.execute(task_callback, task_abort_event)
        else:
            update_task_status(
                task_callback,
                status=task_status,
                result=(result_code, f"{self.action_name} failed"),
            )

    def _trigger_success(
        self, task_callback, task_abort_event, completed_response_msg: str = ""
    ) -> None:
        """Handle successful completion of the action and optionally trigger the on-success action.

        :param task_callback: Callback function used for reporting.
        :type task_callback: Callable
        :param task_abort_event: Event or flag used to signal task abortion.
        :type task_abort_event: Any
        :param completed_response_msg: Optional message describing completion; defaults to
            "{action_name} completed".
        :type completed_response_msg: str
        """
        final_message = completed_response_msg or f"{self.action_name} completed"
        self.logger.debug(final_message)

        if self.action_on_success:
            msg = f"{self.action_name} complete. Triggering on success action."
            self.logger.debug(msg)
            report_task_progress(msg, self.progress_callback)
            self.action_on_success.execute(task_callback, task_abort_event)
        else:
            report_task_progress(final_message, self.progress_callback)
            update_task_status(
                task_callback,
                status=TaskStatus.COMPLETED,
                result=(ResultCode.OK, final_message),
            )

    def execute(
        self, task_callback: Callable, task_abort_event: Any, completed_response_msg: str = ""
    ):
        """Execute all fanned-out commands associated with this action and track progress.

        :param task_callback: Callback function used for reporting.
        :type task_callback: Callable
        :param task_abort_event: Event or flag used to signal task abortion.
        :type task_abort_event: Any
        :param completed_response_msg: Optional message to use when the action completes
            successfully.
        :type completed_response_msg: str
        """
        if task_abort_event.is_set():
            self.logger.warning(f"Action '{self.action_name}' aborted.")
            report_task_progress(f"{self.action_name} aborted", self.progress_callback)
            update_task_status(
                task_callback,
                status=TaskStatus.ABORTED,
                result=(ResultCode.ABORTED, f"{self.action_name} aborted"),
            )
            return

        update_task_status(task_callback, status=TaskStatus.IN_PROGRESS)
        self.logger.debug(
            f"Starting Action '{self.action_name}' with {len(self.fanned_out_commands)} fanned-out"
            " commands."
        )

        # Fan-out: Dispatch all fanned-out commands
        for cmd in self.fanned_out_commands:
            cmd.execute(task_callback)
            if cmd.failed:
                self._trigger_failure(
                    task_callback,
                    task_abort_event,
                    f"{self.action_name} failed {cmd.cmd_response}",
                )
                return

        fanned_out_commands = [
            f"{cmd.device}.{cmd.command_name}"
            for cmd in self.fanned_out_commands
            if not getattr(cmd, "is_device_ignored", False)
        ]
        report_task_progress(
            f"Fanned out commands: {', '.join(fanned_out_commands)}", self.progress_callback
        )

        # If we're not waiting for anything, finish up
        # if all([c.timeout_s <= 0 for c in self.fanned_out_commands]):
        if self.timeout_s <= 0:
            self._trigger_success(task_callback, task_abort_event, completed_response_msg)
            return

        # Report what we are waiting for
        if self.awaited_component_state:
            awaited_attributes = list(self.awaited_component_state.keys())
            awaited_values = list(self.awaited_component_state.values())
            report_awaited_attributes(self.progress_callback, awaited_attributes, awaited_values)

        deadline = time.time() + self.timeout_s
        while deadline > time.time():
            # Handle abort
            if task_abort_event.is_set():
                self.logger.warning(f"Action '{self.action_name}' aborted.")
                report_task_progress(f"{self.action_name} aborted", self.progress_callback)
                update_task_status(
                    task_callback,
                    status=TaskStatus.ABORTED,
                    result=(ResultCode.ABORTED, f"{self.action_name} aborted"),
                )
                return

            # Update status of all running commands
            for cmd in self.fanned_out_commands:
                cmd.report_progress(task_callback)

            # Handle any failed fanned out command
            if any([cmd.failed for cmd in self.fanned_out_commands]):
                command_statuses = {
                    f"{sc.device}.{sc.command_name}": sc.status.name
                    for sc in self.fanned_out_commands
                }
                message = (
                    f"Action '{self.action_name}' failed. Fanned out commands: {command_statuses}"
                )
                self._trigger_failure(task_callback, task_abort_event, message)
                return

            # Check if all commands have succeeded
            if all([cmd.successful for cmd in self.fanned_out_commands]):
                if self.awaited_component_state is None or check_component_state_matches_awaited(
                    self.component_state, self.awaited_component_state
                ):
                    self._trigger_success(task_callback, task_abort_event, completed_response_msg)
                    return

            if self.waiting_callback:
                self.waiting_callback()

            task_abort_event.wait(timeout=1)

            for cmd in self.fanned_out_commands:
                if not cmd.finished:
                    if hasattr(cmd, "device_component_manager"):
                        device_component_manager = getattr(cmd, "device_component_manager")
                        device_component_manager.update_state_from_monitored_attributes(
                            tuple(cmd.awaited_component_state.keys())
                        )

        # Handle timeout
        command_statuses = {
            f"{sc.device}.{sc.command_name}": sc.status.name for sc in self.fanned_out_commands
        }
        message = f"Action '{self.action_name}' timed out. Fanned out commands: {command_statuses}"
        self._trigger_failure(task_callback, task_abort_event, message)


# -------------------------
# Concrete Actions
# -------------------------
class SetStandbyLPModeAction(Action):
    """Transition the dish to STANDBY_LP mode."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        timeout_s: float = DEFAULT_ACTION_TIMEOUT_S,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        super().__init__(
            logger,
            dish_manager_cm,
            timeout_s,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )

        self.spf_command = FannedOutSlowCommand(
            logger=self.logger,
            device="SPF",
            command_name="SetStandbyLPMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["SPF"],
            command_argument=None,
            awaited_component_state={"operatingmode": SPFOperatingMode.STANDBY_LP},
            progress_callback=self._progress_callback,
            is_device_ignored=self.dish_manager_cm.is_device_ignored("SPF"),
        )

        self.spfrx_command = FannedOutSlowCommand(
            logger=self.logger,
            device="SPFRX",
            command_name="SetStandbyMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["SPFRX"],
            command_argument=None,
            awaited_component_state={"operatingmode": SPFRxOperatingMode.STANDBY},
            progress_callback=self._progress_callback,
            is_device_ignored=self.dish_manager_cm.is_device_ignored("SPFRX"),
        )

        self.ds_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="SetStandbyMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            command_argument=None,
            awaited_component_state={
                "operatingmode": DSOperatingMode.STANDBY,
                "powerstate": DSPowerState.LOW_POWER,
            },
            progress_callback=self._progress_callback,
        )

        self._handler = ActionHandler(
            self.logger,
            "SetStandbyLPMode",
            [self.spf_command, self.spfrx_command, self.ds_command],
            # use _dish_manager_cm._component_state to pass the dict by reference
            # _dish_manager_cm.component_state will use the tango base property which will do a
            # deep copy
            component_state=self.dish_manager_cm._component_state,
            awaited_component_state={"dishmode": DishMode.STANDBY_LP},
            action_on_success=self.action_on_success,
            action_on_failure=self.action_on_failure,
            waiting_callback=self.waiting_callback,
            progress_callback=self._progress_callback,
            timeout_s=self.timeout_s,
        )

    def execute(self, task_callback, task_abort_event, completed_response_msg: str = ""):
        if not self.dish_manager_cm.is_device_ignored("SPFRX"):
            spfrx_cm = self.dish_manager_cm.sub_component_managers["SPFRX"]
            if spfrx_cm._component_state["adminmode"] == AdminMode.ENGINEERING:
                try:
                    spfrx_cm.write_attribute_value("adminmode", AdminMode.ONLINE)
                except tango.DevFailed:
                    self.handler._trigger_failure(
                        task_callback,
                        task_abort_event,
                        "Failed to transition SPFRx from AdminMode ENGINEERING to ONLINE",
                    )
                    return

        return super().execute(task_callback, task_abort_event, completed_response_msg)


class SetStandbyFPModeAction(Action):
    """Transition the dish to STANDBY_FP mode."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        timeout_s: float = DEFAULT_ACTION_TIMEOUT_S,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        super().__init__(
            logger,
            dish_manager_cm,
            timeout_s,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )
        ds_set_standby_mode = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="SetStandbyMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            awaited_component_state={"operatingmode": DSOperatingMode.STANDBY},
            progress_callback=self._progress_callback,
            is_device_ignored=self.dish_manager_cm.is_device_ignored("DS"),
        )
        # Action to set the power mode of DS to Full Power
        dsc_power_limit = dish_manager_cm._component_state.get(
            "dscpowerlimitkw", DSC_MIN_POWER_LIMIT_KW
        )
        ds_set_full_power_mode = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="SetPowerMode",
            command_argument=[False, dsc_power_limit],
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            awaited_component_state={"powerstate": DSPowerState.FULL_POWER},
            progress_callback=self._progress_callback,
            is_device_ignored=self.dish_manager_cm.is_device_ignored("DS"),
        )

        self._handler = ActionHandler(
            self.logger,
            "SetStandbyFPMode",
            [ds_set_standby_mode, ds_set_full_power_mode],
            # use _dish_manager_cm._component_state to pass the dict by reference
            # _dish_manager_cm.component_state will use the tango base property which will do a
            # deep copy
            component_state=self.dish_manager_cm._component_state,
            awaited_component_state={"dishmode": DishMode.STANDBY_FP},
            action_on_success=self.action_on_success,
            action_on_failure=self.action_on_failure,
            waiting_callback=self.waiting_callback,
            progress_callback=self._progress_callback,
            timeout_s=self.timeout_s,
        )


class SetOperateModeAction(Action):
    """Transition the dish to OPERATE mode."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        timeout_s: float = DEFAULT_ACTION_TIMEOUT_S,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        super().__init__(
            logger,
            dish_manager_cm,
            timeout_s,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )

        spf_command = FannedOutSlowCommand(
            logger=self.logger,
            device="SPF",
            command_name="SetOperateMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["SPF"],
            awaited_component_state={"operatingmode": SPFOperatingMode.OPERATE},
            progress_callback=self._progress_callback,
            is_device_ignored=self.dish_manager_cm.is_device_ignored("SPF"),
        )
        ds_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="SetPointMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            awaited_component_state={"operatingmode": DSOperatingMode.POINT},
            progress_callback=self._progress_callback,
        )

        self._handler = ActionHandler(
            self.logger,
            "SetOperateMode",
            [spf_command, ds_command],
            # use _dish_manager_cm._component_state to pass the dict by reference
            # _dish_manager_cm.component_state will use the tango base property which will do a
            # deep copy
            component_state=self.dish_manager_cm._component_state,
            awaited_component_state={"dishmode": DishMode.OPERATE},
            action_on_success=self.action_on_success,
            action_on_failure=self.action_on_failure,
            waiting_callback=self.waiting_callback,
            progress_callback=self._progress_callback,
            timeout_s=self.timeout_s,
        )

    def execute(self, task_callback, task_abort_event, completed_response_msg: str = ""):
        if self.dish_manager_cm._component_state["configuredband"] in [Band.NONE, Band.UNKNOWN]:
            self.handler._trigger_failure(
                task_callback,
                task_abort_event,
                "No configured band: SetOperateMode execution not allowed",
                task_status=TaskStatus.REJECTED,
                result_code=ResultCode.NOT_ALLOWED,
            )
            return
        return super().execute(task_callback, task_abort_event, completed_response_msg)


class SetMaintenanceModeAction(Action):
    """Transition the dish to MAINTENANCE mode."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        timeout_s: float = DEFAULT_ACTION_TIMEOUT_S,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        super().__init__(
            logger,
            dish_manager_cm,
            timeout_s,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )
        ds_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="Stow",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            awaited_component_state={"operatingmode": DSOperatingMode.STOW},
            progress_callback=self._progress_callback,
        )
        spfrx_command = FannedOutSlowCommand(
            logger=self.logger,
            device="SPFRX",
            command_name="SetStandbyMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["SPFRX"],
            awaited_component_state={"operatingmode": SPFRxOperatingMode.STANDBY},
            progress_callback=self._progress_callback,
            is_device_ignored=self.dish_manager_cm.is_device_ignored("SPFRX"),
        )
        spf_command = FannedOutSlowCommand(
            logger=self.logger,
            device="SPF",
            command_name="SetMaintenanceMode",
            device_component_manager=self.dish_manager_cm.sub_component_managers["SPF"],
            awaited_component_state={"operatingmode": SPFOperatingMode.MAINTENANCE},
            progress_callback=self._progress_callback,
            is_device_ignored=self.dish_manager_cm.is_device_ignored("SPF"),
        )

        self._handler = ActionHandler(
            self.logger,
            "SetMaintenanceMode",
            [ds_command, spfrx_command, spf_command],
            # use _dish_manager_cm._component_state to pass the dict by reference
            # _dish_manager_cm.component_state will use the tango base property which will do a
            # deep copy
            component_state=self.dish_manager_cm._component_state,
            awaited_component_state={"dishmode": DishMode.STOW},
            action_on_success=self.action_on_success,
            action_on_failure=self.action_on_failure,
            waiting_callback=self.waiting_callback,
            progress_callback=self._progress_callback,
            timeout_s=timeout_s,
        )

    def execute(self, task_callback, task_abort_event, completed_response_msg: str = ""):
        if not self.dish_manager_cm.is_device_ignored("SPFRX"):
            # TODO: Wait for the SPFRx to implement maintenance mode
            self.logger.debug("Nothing done on SPFRx, awaiting implementation on it.")

        return super().execute(task_callback, task_abort_event, completed_response_msg)


class TrackAction(Action):
    """Transition the dish to Track mode."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        """:param logger: Logger instance.
        :type logger: logging.Logger
        :param dish_manager_cm: The DishManagerComponentManager instance.
        :type dish_manager_cm: DishManagerComponentManager
        :param action_on_success: Optional Action to execute automatically if this action succeeds.
        :type action_on_success: Optional[Action]
        :param action_on_failure: Optional Action to execute automatically if this action fails.
        :type action_on_failure: Optional[Action]
        :param waiting_callback: Optional callback executed periodically while waiting on commands.
        :type waiting_callback: Optional[Callable]
        """
        super().__init__(
            logger,
            dish_manager_cm,
            0,  # no timeout for the track action since there is no awaited_component_state
            action_on_success,
            action_on_failure,
            waiting_callback,
        )
        ds_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="Track",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            progress_callback=self._progress_callback,
        )

        self._handler = ActionHandler(
            self.logger,
            "Track",
            [ds_command],
            # use _dish_manager_cm._component_state to pass the dict by reference
            # _dish_manager_cm.component_state will use the tango base property which will do a
            # deep copy
            component_state=self.dish_manager_cm._component_state,
            action_on_success=self.action_on_success,
            action_on_failure=self.action_on_failure,
            waiting_callback=self.waiting_callback,
            progress_callback=self._progress_callback,
        )
        self.completed_message = (
            "Track command has been executed on DS. "
            "Monitor the achievedTargetLock attribute to determine when the dish is on source."
        )

    def execute(self, task_callback, task_abort_event, completed_response_msg: str = ""):
        return super().execute(
            task_callback, task_abort_event, completed_response_msg=self.completed_message
        )


class TrackStopAction(Action):
    """Stop Tracking."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        timeout_s: float = DEFAULT_ACTION_TIMEOUT_S,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        super().__init__(
            logger,
            dish_manager_cm,
            timeout_s,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )
        ds_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="TrackStop",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            awaited_component_state={"pointingstate": PointingState.READY},
            progress_callback=self._progress_callback,
        )

        self._handler = ActionHandler(
            self.logger,
            "TrackStop",
            [ds_command],
            # use _dish_manager_cm._component_state to pass the dict by reference
            # _dish_manager_cm.component_state will use the tango base property which will do a
            # deep copy
            component_state=self.dish_manager_cm._component_state,
            awaited_component_state={"pointingstate": PointingState.READY},
            action_on_success=self.action_on_success,
            action_on_failure=self.action_on_failure,
            waiting_callback=self.waiting_callback,
            progress_callback=self._progress_callback,
            timeout_s=timeout_s,
        )


class ConfigureBandAction(Action):
    """Configure band on DS and SPFRx."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        requested_cmd: str,
        band: Optional[Band] = None,
        synchronise: Optional[bool] = None,
        data: Optional[str] = None,
        timeout_s: float = DEFAULT_ACTION_TIMEOUT_S,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        super().__init__(
            logger,
            dish_manager_cm,
            timeout_s,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )
        self.band = band
        self.synchronise = synchronise
        self.data = data
        # If data is provided then band and synchronise are ignored
        assert (self.data is not None) or (
            self.band is not None and self.synchronise is not None
        ), "Either data or both band and synchronise must be provided"

        self.indexer_enum = IndexerPosition(int(band)) if band is not None else None
        self.requested_cmd = requested_cmd

        if self.data is not None:
            data_json = json.loads(self.data)
            dish_data = data_json.get("dish")
            receiver_band = dish_data.get("receiver_band")
            # Override band and indexer_enum if json data is provided
            self.band = Band[f"B{receiver_band}"]
            self.indexer_enum = IndexerPosition[f"B{receiver_band}"]

            spfrx_configure_band_command = FannedOutSlowCommand(
                logger=self.logger,
                device="SPFRX",
                command_name=self.requested_cmd,
                device_component_manager=self.dish_manager_cm.sub_component_managers["SPFRX"],
                command_argument=self.data,
                awaited_component_state={"configuredband": self.band},
                progress_callback=self._progress_callback,
                is_device_ignored=self.dish_manager_cm.is_device_ignored("SPFRX"),
            )
        else:
            spfrx_configure_band_command = FannedOutSlowCommand(
                logger=self.logger,
                device="SPFRX",
                command_name=self.requested_cmd,
                device_component_manager=self.dish_manager_cm.sub_component_managers["SPFRX"],
                command_argument=self.synchronise,
                awaited_component_state={"configuredband": self.band},
                progress_callback=self._progress_callback,
                is_device_ignored=self.dish_manager_cm.is_device_ignored("SPFRX"),
            )

        ds_set_index_position_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="SetIndexPosition",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            command_argument=self.indexer_enum,
            awaited_component_state={"indexerposition": self.indexer_enum},
            progress_callback=self._progress_callback,
        )

        self._handler = ActionHandler(
            logger=self.logger,
            action_name=self.requested_cmd,
            fanned_out_commands=[ds_set_index_position_command, spfrx_configure_band_command],
            component_state=self.dish_manager_cm._component_state,
            awaited_component_state={"configuredband": self.band},
            action_on_success=action_on_success,
            action_on_failure=action_on_failure,
            waiting_callback=self.waiting_callback,
            progress_callback=self._progress_callback,
            timeout_s=timeout_s,
        )

    def execute(self, task_callback, task_abort_event, completed_response_msg: str = ""):
        self.logger.info(f"{self.requested_cmd} called")
        return super().execute(task_callback, task_abort_event, completed_response_msg)


class ConfigureBandActionSequence(Action):
    """Sequence to set the dish power, configure a band, and then go to operate mode."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        requested_cmd: str,
        band: Optional[Band] = None,
        synchronise: Optional[bool] = None,
        data: Optional[str] = None,
        timeout_s: float = DEFAULT_ACTION_TIMEOUT_S,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        super().__init__(
            logger,
            dish_manager_cm,
            timeout_s,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )
        self.band = band
        self.synchronise = synchronise
        self.data = data
        self.indexer_enum = IndexerPosition(int(band)) if band is not None else None
        self.requested_cmd = requested_cmd

    def execute(self, task_callback, task_abort_event, completed_response_msg: str = ""):
        """Execute the defined action."""
        current_dish_mode = self.dish_manager_cm._component_state["dishmode"]

        # Step 2: Operate mode action (final step)
        operate_action = SetOperateModeAction(
            logger=self.logger,
            dish_manager_cm=self.dish_manager_cm,
            action_on_success=self.action_on_success,
            action_on_failure=self.action_on_failure,
            waiting_callback=self.waiting_callback,
            timeout_s=self.timeout_s,
        )

        final_action = operate_action if current_dish_mode != DishMode.STOW else None

        # Step 1: Configure band action
        configure_action = ConfigureBandAction(
            logger=self.logger,
            dish_manager_cm=self.dish_manager_cm,
            band=self.band,
            synchronise=self.synchronise,
            data=self.data,
            requested_cmd=self.requested_cmd,
            action_on_success=final_action,  # chain operate action if we aren't in STOW
            waiting_callback=self.waiting_callback,
            timeout_s=self.timeout_s,
        )

        # Step 0: Pre-action if we need LP -> FP
        if current_dish_mode == DishMode.STANDBY_LP:
            pre_action = SetStandbyFPModeAction(
                logger=self.logger,
                dish_manager_cm=self.dish_manager_cm,
                action_on_success=configure_action,  # chain configure action
                waiting_callback=self.waiting_callback,
                timeout_s=self.timeout_s,
            )
            return pre_action.execute(task_callback, task_abort_event, completed_response_msg)

        # If no LP -> FP transition is needed then start with ConfigureBand
        return configure_action.execute(task_callback, task_abort_event, completed_response_msg)


class SlewAction(Action):
    """Slew the dish to the specified target coordinates."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        target: list[float],
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        """:param logger: Logger instance.
        :type logger: logging.Logger
        :param dish_manager_cm: The DishManagerComponentManager instance.
        :type dish_manager_cm: DishManagerComponentManager
        :target: The target coordinates to slew to.
        :type target: list[float]
        :param action_on_success: Optional Action to execute automatically if this action succeeds.
        :type action_on_success: Optional[Action]
        :param action_on_failure: Optional Action to execute automatically if this action fails.
        :type action_on_failure: Optional[Action]
        :param waiting_callback: Optional callback executed periodically while waiting on commands.
        :type waiting_callback: Optional[Callable]
        """
        super().__init__(
            logger,
            dish_manager_cm,
            0,  # no timeout for the slew action since there is no awaited_component_state
            action_on_success,
            action_on_failure,
            waiting_callback,
        )

        ds_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="Slew",
            device_component_manager=self.dish_manager_cm.sub_component_managers["DS"],
            command_argument=target,
            progress_callback=self._progress_callback,
        )

        self._handler = ActionHandler(
            logger=self.logger,
            action_name="Slew",
            fanned_out_commands=[ds_command],
            component_state=self.dish_manager_cm._component_state,
            action_on_success=action_on_success,
            action_on_failure=action_on_failure,
            waiting_callback=self.waiting_callback,
            progress_callback=self._progress_callback,
        )
        self.completed_message = (
            f"The DS has been commanded to Slew to {target}. "
            "Monitor the pointing attributes for the completion status of the task."
        )

    def execute(self, task_callback, task_abort_event, completed_response_msg: str = ""):
        return super().execute(
            task_callback, task_abort_event, completed_response_msg=self.completed_message
        )


class TrackLoadStaticOffAction(Action):
    """TrackLoadStaticOff action."""

    def __init__(
        self,
        logger: logging.Logger,
        dish_manager_cm,
        off_xel,
        off_el,
        timeout_s: float = DEFAULT_ACTION_TIMEOUT_S,
        action_on_success: Optional["Action"] = None,
        action_on_failure: Optional["Action"] = None,
        waiting_callback: Optional[Callable] = None,
    ):
        super().__init__(
            logger,
            dish_manager_cm,
            timeout_s,
            action_on_success,
            action_on_failure,
            waiting_callback,
        )

        ds_command = FannedOutSlowCommand(
            logger=self.logger,
            device="DS",
            command_name="TrackLoadStaticOff",
            device_component_manager=dish_manager_cm.sub_component_managers["DS"],
            command_argument=[off_xel, off_el],
            awaited_component_state={
                "actstaticoffsetvaluexel": off_xel,
                "actstaticoffsetvalueel": off_el,
            },
            progress_callback=self._progress_callback,
        )

        self._handler = ActionHandler(
            logger=self.logger,
            action_name="TrackLoadStaticOff",
            fanned_out_commands=[ds_command],
            component_state=self.dish_manager_cm._component_state,
            awaited_component_state={
                "actstaticoffsetvaluexel": off_xel,
                "actstaticoffsetvalueel": off_el,
            },
            action_on_success=action_on_success,
            action_on_failure=action_on_failure,
            waiting_callback=self.waiting_callback,
            progress_callback=self._progress_callback,
            timeout_s=timeout_s,
        )
