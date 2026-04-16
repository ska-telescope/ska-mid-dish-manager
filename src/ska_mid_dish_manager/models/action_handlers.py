"""Module containing the action handlers."""

import logging
import time
from abc import ABC
from typing import Any, Callable, List, Optional

from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.models.constants import (
    DEFAULT_ACTION_TIMEOUT_S,
    OPERATOR_TAG,
)
from ska_mid_dish_manager.models.fanned_out_command import (
    FannedOutCommand,
)
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
            raise NotImplementedError(f"Action {self.__class__} does not have a handler")
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
        final_message = completed_response_msg or f"{self.action_name} completed."
        self.logger.info(final_message, extra=OPERATOR_TAG)

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
            self.logger.warning(f"Action '{self.action_name}' aborted.", extra=OPERATOR_TAG)
            report_task_progress(f"{self.action_name} aborted", self.progress_callback)
            update_task_status(
                task_callback,
                status=TaskStatus.ABORTED,
                result=(ResultCode.ABORTED, f"{self.action_name} aborted"),
            )
            return

        update_task_status(task_callback, status=TaskStatus.IN_PROGRESS)

        fanned_out_commands = [
            f"{cmd.device}.{cmd.command_name}"
            for cmd in self.fanned_out_commands
            if not getattr(cmd, "is_device_ignored", False)
        ]
        fanned_out_commands_str = ", ".join(fanned_out_commands) if fanned_out_commands else "None"
        self.logger.info(
            f"Starting Action {self.action_name}. Fanning out {fanned_out_commands_str} commands.",
            extra=OPERATOR_TAG,
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

        report_task_progress(
            f"Fanned out commands: {fanned_out_commands_str}", self.progress_callback
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
                self.logger.warning(f"Action '{self.action_name}' aborted.", extra=OPERATOR_TAG)
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
            if any(cmd.failed for cmd in self.fanned_out_commands):
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
            if all(cmd.successful for cmd in self.fanned_out_commands):
                if self.awaited_component_state is None or check_component_state_matches_awaited(
                    self.component_state, self.awaited_component_state
                ):
                    self._trigger_success(task_callback, task_abort_event, completed_response_msg)
                    return

            if self.waiting_callback:
                self.waiting_callback()

            task_abort_event.wait(timeout=1)

        # update the component state from an attribute read before giving up
        # this is a fallback in case the change event subscriptions missed updates
        for cmd in self.fanned_out_commands:
            if not cmd.finished:
                if hasattr(cmd, "device_component_manager"):
                    device_component_manager = getattr(cmd, "device_component_manager")
                    device_component_manager.update_state_from_monitored_attributes(
                        tuple(cmd.awaited_component_state.keys())
                    )
        if all([cmd.successful for cmd in self.fanned_out_commands]):
            if self.awaited_component_state is None or check_component_state_matches_awaited(
                self.component_state, self.awaited_component_state
            ):
                self._trigger_success(task_callback, task_abort_event, completed_response_msg)
                return

        # Handle timeout
        command_statuses = {
            f"{sc.device}.{sc.command_name}": sc.status.name for sc in self.fanned_out_commands
        }
        message = f"Action '{self.action_name}' timed out. Fanned out commands: {command_statuses}"
        self._trigger_failure(task_callback, task_abort_event, message)


class SequentialActionHandler(ActionHandler):
    """Action handler that executes the FannedOutCommands in sequence."""

    def execute(
        self, task_callback: Callable, task_abort_event: Any, completed_response_msg: str = ""
    ):
        """Execute all fanned-out commands associated with this action in order.


        :param task_callback: Callback function used for reporting.
        :type task_callback: Callable
        :param task_abort_event: Event or flag used to signal task abortion.
        :type task_abort_event: Any
        :param completed_response_msg: Optional message to use when the action completes
            successfully.
        :type completed_response_msg: str
        """
        if task_abort_event.is_set():
            self.logger.warning(f"Action '{self.action_name}' aborted.", extra=OPERATOR_TAG)
            report_task_progress(f"{self.action_name} aborted", self.progress_callback)
            update_task_status(
                task_callback,
                status=TaskStatus.ABORTED,
                result=(ResultCode.ABORTED, f"{self.action_name} aborted"),
            )
            return

        update_task_status(task_callback, status=TaskStatus.IN_PROGRESS)

        sequential_commands = [
            f"{cmd.device}.{cmd.command_name}"
            for cmd in self.fanned_out_commands
            if not getattr(cmd, "is_device_ignored", False)
        ]
        sequential_commands_str = ", ".join(sequential_commands) if sequential_commands else "None"
        self.logger.info(
            (
                f"Starting Action {self.action_name}. Running"
                f" in order {sequential_commands_str} commands."
            ),
            extra=OPERATOR_TAG,
        )

        for cmd in self.fanned_out_commands:
            cmd.execute(task_callback)
            if cmd.failed:
                self._trigger_failure(
                    task_callback,
                    task_abort_event,
                    f"{self.action_name} failed {cmd.cmd_response}",
                )
                return

            report_task_progress(
                f"Running {cmd.command_name} on device {cmd.device}", self.progress_callback
            )

            if cmd.timeout_s <= 0:
                report_task_progress(
                    f"Not waiting for: {cmd} as the timeout is 0", self.progress_callback
                )
                continue

            if cmd.awaited_component_state:
                awaited_attributes = list(cmd.awaited_component_state.keys())
                awaited_values = list(cmd.awaited_component_state.values())
                report_awaited_attributes(
                    self.progress_callback, awaited_attributes, awaited_values, device=cmd.device
                )

            deadline = time.time() + cmd.timeout_s
            while deadline > time.time():
                # Handle abort
                if task_abort_event.is_set():
                    self.logger.warning(
                        f"Action '{self.action_name}' aborted.", extra=OPERATOR_TAG
                    )
                    report_task_progress(f"{self.action_name} aborted", self.progress_callback)
                    update_task_status(
                        task_callback,
                        status=TaskStatus.ABORTED,
                        result=(ResultCode.ABORTED, f"{self.action_name} aborted"),
                    )
                    return

                cmd.report_progress(task_callback)

                if cmd.failed or cmd.successful:
                    break
                task_abort_event.wait(timeout=1)

            if cmd.failed:
                message = (
                    f"Action '{self.action_name}' failed. "
                    f"{cmd.command_name} on device {cmd.device} failed."
                )
                self._trigger_failure(task_callback, task_abort_event, message)
                return

            if cmd.successful:
                report_task_progress(
                    f"{self.action_name}: {cmd.command_name} on device {cmd.device} completed",
                    self.progress_callback,
                )
                continue

            update_task_status(
                task_callback,
                status=TaskStatus.FAILED,
                result=(
                    ResultCode.FAILED,
                    f"{self.action_name}: {cmd.command_name} on device {cmd.device} timed out",
                ),
            )

        self._trigger_success(task_callback, task_abort_event, completed_response_msg)
        return
