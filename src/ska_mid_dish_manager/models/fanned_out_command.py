"""Abstracts all the logic for executing a command on a device."""

import enum
import logging
import time
from typing import Any, Callable

from ska_control_model import TaskStatus
from ska_tango_base.base.base_component_manager import BaseComponentManager
from ska_tango_base.commands import SubmittedSlowCommand

from ska_mid_dish_manager.models.dish_enums import (
    FannedOutCommandStatus,
)
from ska_mid_dish_manager.utils.action_helpers import (
    check_component_state_matches_awaited,
    convert_enums_to_names,
)


class FannedOutCommand:
    """Defines a single command to be fanned out as part of a Action."""

    def __init__(
        self,
        logger: logging.Logger,
        device: str,
        name: str,
        command: Callable,
        timeout_s: float,
        component_state: dict,
        command_argument: Any = None,
        awaited_component_state: dict = {},
    ):
        """:param logger: Logger instance
        :type logger: Logger
        :param device: The name for the device this command is executed on
        :type device: str
        :param name: The name for the command
        :type name: str
        :param command: Command to run as part of `execute`
        :type command: str
        :param timeout_s: Timeout (in seconds) for the command execution
        :type timeout_s: float
        :param component_state: The component state containing the attributes to wait for updates
            on.
        :type component_state: Optional[dict]
        :param command_argument: Argument for the requested command
        :type command_argument: Any
        :param awaited_component_state: The component state containing the attributes and values to
            wait for.
        :type awaited_component_state: dict
        """
        self.logger = logger
        self.device = device
        self.name = name
        self.command = command
        self.command_argument = command_argument
        self.timeout_s = timeout_s
        self.start_time: float = 0.0
        self.id = None
        self._status = FannedOutCommandStatus.PENDING
        self._task_finish_reported = False
        self.cmd_response = ""
        self.component_state = component_state
        self.awaited_component_state = awaited_component_state
        self.awaited_update_reports = {attr: False for attr in awaited_component_state.keys()}

    def execute(self, task_callback: Callable) -> None:
        """Execute the fanned out command."""
        self.logger.debug(f"Executing {self.name} with arg {self.command_argument}")
        self._status = FannedOutCommandStatus.RUNNING
        self.start_time = time.time()

        try:
            res = None
            if self.command_argument is not None:
                res = self.command(task_callback, self.command_argument)
            else:
                res = self.command(task_callback)
            assert len(res) == 2, (
                f"FannedOutCommand 'command' Callable expects a response of len 2, but got '{res}'"
            )
            self.cmd_response, self.id = res
        except RuntimeError as e:
            self.logger.exception(f"FannedOutCommand '{self.name}' failed to execute: {e}")
            self._status = FannedOutCommandStatus.FAILED
            self.cmd_response = f"{self.name} failed {e.args[0]}"

    @property
    def status(self) -> FannedOutCommandStatus:
        """Get the status of the fanned out command."""
        return self._status

    def _update_status(self, task_callback: Callable) -> None:
        if self._status == FannedOutCommandStatus.RUNNING:
            # timeout
            if time.time() - self.start_time > self.timeout_s:
                self._status = FannedOutCommandStatus.TIMED_OUT
            # completed
            if check_component_state_matches_awaited(
                self.component_state, self.awaited_component_state
            ):
                self._status = FannedOutCommandStatus.COMPLETED
        if self._status in [FannedOutCommandStatus.FAILED, FannedOutCommandStatus.TIMED_OUT]:
            task_callback(
                progress=(
                    f"{self.device} device failed executing {self.name} command with ID {self.id}"
                )
            )

    @property
    def failed(self) -> bool:
        """Check if the fanned out command has failed."""
        return self.status in (FannedOutCommandStatus.TIMED_OUT, FannedOutCommandStatus.FAILED)

    @property
    def successful(self) -> bool:
        """Check if the fanned out command has failed."""
        return self.status in (FannedOutCommandStatus.COMPLETED, FannedOutCommandStatus.IGNORED)

    @property
    def finished(self) -> bool:
        """Check if the fanned out command has finished."""
        return self.failed or self.successful

    def report_progress(self, task_callback: Callable) -> None:
        """Report the progress of fanned out command."""
        self._update_status(task_callback)
        current_comp_state = dict(self.component_state)

        # Awaited component state updates
        for attr_name, reported_update in self.awaited_update_reports.items():
            if not reported_update and attr_name in self.awaited_component_state:
                expected_value = self.awaited_component_state[attr_name]
                if attr_name in current_comp_state:
                    current_value = current_comp_state[attr_name]
                    if current_value == expected_value:
                        if isinstance(current_value, enum.IntEnum):
                            current_value = current_value.name
                        task_callback(
                            progress=f"{self.device} {attr_name} changed to {current_value}"
                        )
                        self.awaited_update_reports[attr_name] = True
        if self.finished and not self._task_finish_reported:
            task_callback(progress=f"{self.name} {self.status.name.lower()}")
            self._task_finish_reported = True


class FannedOutSlowCommand(FannedOutCommand):
    def __init__(
        self,
        logger: logging.Logger,
        device: str,
        command_name: str,
        device_component_manager: BaseComponentManager,
        timeout_s: float,
        command_tracker: Any,
        command_argument: Any = None,
        awaited_component_state: dict = {},
        is_device_ignored: bool = False,
    ):
        """:param logger: Logger instance
        :type logger: Logger
        :param device: The name for the device this command is executed on
        :type device: str
        :param command_name: The name for the command to be executed
        :type command_name: str
        :param device_component_manager: The component manager of the subservient device
        :type device_component_manager: BaseComponentManager
        :param timeout_s: Timeout (in seconds) for the command execution
        :type timeout_s: float
        :param command_tracker: Command tracker object
        :type command_tracker: Any
        :param command_argument: Argument for the requested command
        :type command_argument: Any
        :param awaited_component_state: The component state containing the attributes and values to
            wait for.
        :type awaited_component_state: dict
        :param is_device_ignored: Toggle to ignore fanning out of command if the device is ignored.
        :type is_device_ignored: bool
        """
        self.command_name = command_name
        self.device_component_manager = device_component_manager
        self.command_tracker = command_tracker
        self.is_device_ignored = is_device_ignored

        super().__init__(
            logger=logger,
            device=device,
            name=f"{command_name}",
            command=self._execute_slow_command,
            timeout_s=timeout_s,
            # use device_component_manager._component_state to pass the dict by reference
            # device_component_manager.component_state will use the tango base property which will
            # do a deep copy
            component_state=self.device_component_manager._component_state,
            command_argument=command_argument,
            awaited_component_state=awaited_component_state,
        )

    def _execute_slow_command(self, task_callback: Callable, *args, **kwargs) -> int | None:
        """Fan out the respective command to the subservient devices."""
        if self.is_device_ignored:
            self.logger.debug(
                f"{self.device} device is disabled. {self.command_name} call ignored"
            )
            task_callback(
                progress=f"{self.device} device is disabled. {self.command_name} call ignored"
            )
            self._status = FannedOutCommandStatus.IGNORED
            return (None, None)

        command = SubmittedSlowCommand(
            f"{self.device}_{self.command_name}",
            self.command_tracker,
            self.device_component_manager,
            "run_device_command",
            callback=None,
            logger=self.logger,
        )
        response, command_id = command(self.command_name, self.command_argument)
        # Report that the command has been called on the subservient device
        task_callback(progress=f"{self.command_name} called on {self.device}, ID {command_id}")

        # fail the command immediately, if the subservient device fails
        if response in [TaskStatus.FAILED, TaskStatus.REJECTED]:
            raise RuntimeError(command_id)

        if self.awaited_component_state is not None:
            awaited_attributes = list(self.awaited_component_state.keys())
            awaited_values_list = list(self.awaited_component_state.values())

            # Report which attribute and value the sub device is waiting for
            # e.g. Awaiting DEVICE attra, attrb change to VALUE_1, VALUE_2
            if awaited_values_list != []:
                values_print_string = convert_enums_to_names(awaited_values_list)
                attributes_print_string = ", ".join(map(str, awaited_attributes))
                values_print_string = ", ".join(map(str, values_print_string))

                task_callback(
                    progress=(
                        f"Awaiting {self.device} {attributes_print_string} change to"
                        f" {values_print_string}"
                    )
                )
        return response, command_id

    def _update_status(self, task_callback: Callable) -> None:
        if self._status == FannedOutCommandStatus.RUNNING:
            current_slow_command_status = self.command_tracker.get_command_status(self.id)
            if current_slow_command_status in [TaskStatus.FAILED, TaskStatus.REJECTED]:
                self._status = FannedOutCommandStatus.FAILED
        super()._update_status(task_callback)
