"""Abstracts all the logic for executing a command on a device."""

import enum
import logging
import time
from typing import Any, Callable, Optional

from ska_control_model import TaskStatus

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager
from ska_mid_dish_manager.models.dish_enums import FannedOutCommandStatus
from ska_mid_dish_manager.utils.action_helpers import (
    check_component_state_matches_awaited,
    report_awaited_attributes,
    report_task_progress,
)


class FannedOutCommand:
    """Defines a single command to be fanned out as part of a Action."""

    def __init__(
        self,
        logger: logging.Logger,
        device: str,
        command_name: str,
        command: Callable,
        component_state: dict,
        command_argument: Any = None,
        awaited_component_state: dict = {},
        timeout_s: float = 0,
        progress_callback: Optional[Callable] = None,
    ):
        """:param logger: Logger instance
        :type logger: Logger
        :param device: The name for the device this command is executed on
        :type device: str
        :param command_name: The name for the command
        :type command_name: str
        :param command: Command to run as part of `execute`
        :type command: str
        :param component_state: The component state containing the attributes to wait for updates
            on.
        :type component_state: Optional[dict]
        :param command_argument: Argument for the requested command
        :type command_argument: Any
        :param awaited_component_state: The component state containing the attributes and values to
            wait for.
        :type awaited_component_state: dict
        :param timeout_s: Timeout (in seconds) for the command execution. A value <= 0 will disable
            the timeout.
        :type timeout_s: float
        :param progress_callback: Optional callback to report progress updates.
        :type progress_callback: Callable
        """
        self.logger = logger
        self.device = device
        self.command_name = command_name
        self.command = command
        self.command_argument = command_argument
        self.timeout_s = timeout_s
        self.start_time: float = 0.0
        self.cmd_message = None
        self._status = FannedOutCommandStatus.PENDING
        self._task_finish_reported = False
        self._progress_callback = progress_callback
        self.cmd_response = ""
        self.component_state = component_state
        self.awaited_component_state = awaited_component_state
        self.awaited_update_reports = {attr: False for attr in awaited_component_state.keys()}

    def execute(self, task_callback: Callable) -> None:
        """Execute the fanned out command."""
        self.logger.debug(f"Executing {self.command_name} with arg {self.command_argument}")
        self._status = FannedOutCommandStatus.RUNNING
        self.start_time = time.time()

        try:
            res = self.command(self.command_argument)
            assert len(res) == 2, (
                f"FannedOutCommand 'command' Callable expects a response of len 2, but got '{res}'"
            )
            self.cmd_response, self.cmd_message = res
        except RuntimeError as e:
            self.logger.error(f"FannedOutCommand '{self.command_name}' failed to execute: {e}")
            self._status = FannedOutCommandStatus.FAILED
            self.cmd_response = f"{e.args[0]}"

    @property
    def status(self) -> FannedOutCommandStatus:
        """Get the status of the fanned out command."""
        return self._status

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

    def _update_status(self, task_callback: Callable) -> None:
        if self._status == FannedOutCommandStatus.RUNNING:
            # timeout
            if self.timeout_s > 0 and time.time() - self.start_time > self.timeout_s:
                self._status = FannedOutCommandStatus.TIMED_OUT
            # completed
            if check_component_state_matches_awaited(
                self.component_state, self.awaited_component_state
            ):
                self._status = FannedOutCommandStatus.COMPLETED
        if self._status in [FannedOutCommandStatus.FAILED, FannedOutCommandStatus.TIMED_OUT]:
            report_task_progress(
                f"{self.device} device {self._status.name.lower().replace('_', ' ')}"
                f" executing {self.command_name} command",
                self._progress_callback,
            )

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
                        report_task_progress(
                            f"{self.device} {attr_name} changed to {current_value}",
                            self._progress_callback,
                        )
                        self.awaited_update_reports[attr_name] = True
        if self.finished and not self._task_finish_reported:
            status_name = self.status.name.lower().replace("_", " ")
            report_task_progress(
                f"{self.device}.{self.command_name} {status_name}", self._progress_callback
            )
            self._task_finish_reported = True


class FannedOutSlowCommand(FannedOutCommand):
    def __init__(
        self,
        logger: logging.Logger,
        device: str,
        command_name: str,
        device_component_manager: TangoDeviceComponentManager,
        command_argument: Any = None,
        awaited_component_state: dict = {},
        timeout_s: float = 0,
        progress_callback: Optional[Callable] = None,
        is_device_ignored: bool = False,
    ):
        """:param logger: Logger instance
        :type logger: Logger
        :param device: The name for the device this command is executed on
        :type device: str
        :param command_name: The name for the command to be executed
        :type command_name: str
        :param device_component_manager: The component manager of the subservient device
        :type device_component_manager: TangoDeviceComponentManager
        :param timeout_s: Timeout (in seconds) for the command execution
        :type timeout_s: float
        :param command_argument: Argument for the requested command
        :type command_argument: Any
        :param awaited_component_state: The component state containing the attributes and values to
            wait for.
        :type awaited_component_state: dict
        :param progress_callback: Optional callback to report progress updates.
        :type progress_callback: Callable
        :param is_device_ignored: Toggle to ignore fanning out of command if the device is ignored.
        :type is_device_ignored: bool
        """
        self.device_component_manager = device_component_manager
        self.is_device_ignored = is_device_ignored

        super().__init__(
            logger=logger,
            device=device,
            command_name=f"{command_name}",
            command=self._execute_tango_command,
            # use device_component_manager._component_state to pass the dict by reference
            # device_component_manager.component_state will use the tango base property which will
            # do a deep copy
            component_state=self.device_component_manager._component_state,
            command_argument=command_argument,
            awaited_component_state=awaited_component_state,
            timeout_s=timeout_s,
            progress_callback=progress_callback,
        )

    def _execute_tango_command(self) -> tuple:
        """Fan out the respective command to the subservient devices."""
        if self.is_device_ignored:
            self.logger.debug(
                f"{self.device} device is disabled. {self.command_name} call ignored"
            )
            self._status = FannedOutCommandStatus.IGNORED
            return None, None

        task_status, msg = self.device_component_manager.execute_command(
            self.command_name, self.command_argument
        )
        if self.awaited_component_state is not None:
            awaited_attributes = list(self.awaited_component_state.keys())
            awaited_values = list(self.awaited_component_state.values())
            report_awaited_attributes(
                self._progress_callback, awaited_attributes, awaited_values, self.device
            )

        if task_status == TaskStatus.FAILED:
            raise RuntimeError(msg)
        return task_status, msg
