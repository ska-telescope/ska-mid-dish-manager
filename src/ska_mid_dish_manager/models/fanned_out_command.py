"""Abstracts all the logic for executing a command on a device."""

import enum
import json
import logging
import time
from typing import Any, Callable, Optional

from ska_control_model import ResultCode, TaskStatus

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
        self.executed_cmd_message = None
        self._status = FannedOutCommandStatus.PENDING
        self._task_finish_reported = False
        self._progress_callback = progress_callback
        self.executed_cmd_response = ""
        self.component_state = component_state
        self.awaited_component_state = awaited_component_state
        self.awaited_update_reports = {attr: False for attr in awaited_component_state.keys()}

    def execute(self, task_callback: Callable) -> None:
        """Execute the fanned out command."""
        self.logger.debug(f"Executing {self.command_name} with arg {self.command_argument}")
        self._status = FannedOutCommandStatus.IN_PROGRESS
        self.start_time = time.time()

        try:
            res = self.command()
            assert len(res) == 2, (
                f"FannedOutCommand 'command' Callable expects a response of len 2, but got '{res}'"
            )
            self.executed_cmd_response, self.executed_cmd_message = res

            if self.awaited_component_state is not None:
                awaited_attributes = list(self.awaited_component_state.keys())
                awaited_values = list(self.awaited_component_state.values())
                report_awaited_attributes(
                    self._progress_callback, awaited_attributes, awaited_values, self.device
                )
        except RuntimeError as e:
            self.logger.error(f"FannedOutCommand '{self.command_name}' failed to execute: {e}")
            self._status = FannedOutCommandStatus.FAILED
            self.executed_cmd_response = f"{e.args[0]}"

    @property
    def status(self) -> FannedOutCommandStatus:
        """Get the status of the fanned out command."""
        return self._status

    @property
    def failed(self) -> bool:
        """Check if the fanned out command has failed."""
        return self.status in (
            FannedOutCommandStatus.TIMED_OUT,
            FannedOutCommandStatus.FAILED,
            FannedOutCommandStatus.ABORTED,
            FannedOutCommandStatus.REJECTED,
        )

    @property
    def successful(self) -> bool:
        """Check if the fanned out command has failed."""
        return self.status in (FannedOutCommandStatus.COMPLETED, FannedOutCommandStatus.IGNORED)

    @property
    def finished(self) -> bool:
        """Check if the fanned out command has finished."""
        return self.failed or self.successful

    def _update_status(self, task_callback: Callable) -> None:
        if self._status == FannedOutCommandStatus.IN_PROGRESS:
            # completed
            if check_component_state_matches_awaited(
                self.component_state, self.awaited_component_state
            ):
                self._status = FannedOutCommandStatus.COMPLETED
            # timeout
            if self.timeout_s > 0 and time.time() - self.start_time > self.timeout_s:
                self._status = FannedOutCommandStatus.TIMED_OUT
        # if self._status in [FannedOutCommandStatus.FAILED, FannedOutCommandStatus.TIMED_OUT]:
        #     report_task_progress(
        #         f"{self.device} device {self._status.name.lower().replace('_', ' ')}"
        #         f" executing {self.command_name} command",
        #         self._progress_callback,
        #     )

    def report_progress(self, task_callback: Callable) -> None:
        """Report the progress of fanned out command."""
        current_comp_state = dict(self.component_state)

        # Report awaited component state updates
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

        # Update the commands status
        self._update_status(task_callback)

        # Report if the command has finished
        if self.finished and not self._task_finish_reported:
            status_name = self.status.name.lower().replace("_", " ")
            cmd_response = (
                self.executed_cmd_response
                if self._status
                in [
                    FannedOutCommandStatus.FAILED,
                    FannedOutCommandStatus.REJECTED,
                    FannedOutCommandStatus.ABORTED,
                ]
                else ""
            )
            report_task_progress(
                f"{self.device}.{self.command_name} {status_name}: {cmd_response}",
                self._progress_callback,
            )
            self._task_finish_reported = True


class FannedOutTangoCommand(FannedOutCommand):
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
        if task_status == TaskStatus.FAILED:
            raise RuntimeError(msg)
        return task_status, msg


class FannedOutTangoLongRunningCommand(FannedOutTangoCommand):
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
        self.is_lrc_finished = False
        super().__init__(
            logger=logger,
            device=device,
            command_name=f"{command_name}",
            device_component_manager=device_component_manager,
            command_argument=command_argument,
            awaited_component_state=awaited_component_state,
            timeout_s=timeout_s,
            progress_callback=progress_callback,
            is_device_ignored=is_device_ignored,
        )

    def _execute_tango_command(self) -> tuple:
        """Execute the fanned out command and keep the FannedOutCommandStatus as PENDING."""
        ret = super()._execute_tango_command()
        # This will be updated to IN_PROGRESS or COMPLETED by self._update_status depending on the
        # lrcExecuting and lrcFinished attributes, respectively.
        self._status = FannedOutCommandStatus.QUEUED
        return ret

    def _is_command_in_lrc_executing(self) -> bool:
        lrc_executing = self.device_component_manager.read_attribute_value("lrcexecuting")
        if not isinstance(lrc_executing, tuple):
            self.logger.error(
                "lrcExecuting value is not a tuple, got %s: %s", type(lrc_executing), lrc_executing
            )
            return False

        for executing_cmd in lrc_executing:
            try:
                executing_cmd_dict = json.loads(executing_cmd)
            except json.JSONDecodeError:
                self.logger.exception("Invalid json value for lrcExecuting")
                continue

            if executing_cmd_dict.get("uid") == self.executed_cmd_message:
                return True
        return False

    def _get_command_lrc_finished_dict(self) -> Optional[dict]:
        lrc_finished = self.device_component_manager.read_attribute_value("lrcfinished")
        if not isinstance(lrc_finished, tuple):
            self.logger.error(
                "lrcFinished value is not a list, got %s: %s", type(lrc_finished), lrc_finished
            )
            return None

        for finished_cmd in lrc_finished:
            try:
                finished_cmd_dict = json.loads(finished_cmd)
            except json.JSONDecodeError:
                self.logger.exception("Invalid json value for lrcFinished")
                return None

            if finished_cmd_dict.get("uid") == self.executed_cmd_message:
                return finished_cmd_dict
        return None

    def _update_status(self, task_callback: Callable) -> None:
        # If the command is queued or in
        self.logger.info("Updating status, self._status = %s", self._status)
        if self._status in [FannedOutCommandStatus.QUEUED, FannedOutCommandStatus.IN_PROGRESS]:
            # If the LRC has not yet been reported in lrcFinished
            if not self.is_lrc_finished:
                lrc_finished_dict = self._get_command_lrc_finished_dict()

                self.logger.info("lrc_finished_dict = %s", lrc_finished_dict)
                if lrc_finished_dict:
                    lrc_result = lrc_finished_dict["result"]
                    lrc_status = lrc_finished_dict["status"]

                    self.executed_cmd_response = lrc_result

                    if lrc_status == TaskStatus.COMPLETED.name:
                        # Don't mark it as completed yet, still need to check component state
                        self.is_lrc_finished = True
                    elif lrc_status == TaskStatus.ABORTED.name:
                        self._status = FannedOutCommandStatus.ABORTED
                        return
                    elif lrc_status == TaskStatus.REJECTED.name:
                        self._status = FannedOutCommandStatus.REJECTED
                        return
                    elif lrc_status == TaskStatus.FAILED.name:
                        self._status = FannedOutCommandStatus.FAILED
                        return
                elif self._is_command_in_lrc_executing():
                    self._status = FannedOutCommandStatus.IN_PROGRESS

            # Final check
            component_ready = check_component_state_matches_awaited(
                self.component_state,
                self.awaited_component_state,
            )

            if self.is_lrc_finished and component_ready:
                self._status = FannedOutCommandStatus.COMPLETED
                return

            # timeout
            if self.timeout_s > 0 and time.time() - self.start_time > self.timeout_s:
                self._status = FannedOutCommandStatus.TIMED_OUT


class DishManagerCMMethod(FannedOutCommand):
    """Class that executes the method, args and kwargs passed to it.

    This class specifically handles the case where the method responds with a result or raises
    an exception.
    """

    def __init__(
        self,
        logger,
        method,
        component_state,
        command_args=(),
        command_kwargs={},
        awaited_component_state={},
        timeout_s=0,
    ):
        self.command_args = command_args
        self.command_kwargs = command_kwargs
        super().__init__(
            logger,
            "DishManager",
            str(method),
            method,
            component_state,
            None,
            awaited_component_state,
            timeout_s,
        )

    def execute(self, task_callback) -> None:
        """Execute the command."""
        self.logger.debug(
            (
                f"Executing {self.command_name} with args {self.command_args} "
                f"and kwargs. {self.command_kwargs}"
            )
        )
        self._status = FannedOutCommandStatus.IN_PROGRESS
        self.start_time = time.time()
        try:
            res = self.command(*self.command_args, **self.command_kwargs)
            self.logger.debug(f"Result: {res}")
            self.executed_cmd_response = res
            self._status = FannedOutCommandStatus.COMPLETED
        except Exception as e:
            self.logger.exception(f"FannedOutCommand '{self.command_name}' failed to execute: {e}")
            self._status = FannedOutCommandStatus.FAILED
            self.executed_cmd_response = f"{e}"


class DishManagerCMMethodCallBack(FannedOutCommand):
    """Class that executes the method, args and kwargs passed to it.

    This class specifically handles the case where the task_callback is used to
    track method result.
    """

    def __init__(
        self,
        logger,
        method,
        component_state,
        command_args=(),
        command_kwargs={},
        awaited_component_state={},
        timeout_s=0,
    ):
        self.command_args = command_args
        self.command_kwargs = command_kwargs
        super().__init__(
            logger,
            "DishManager",
            str(method),
            method,
            component_state,
            None,
            awaited_component_state,
            timeout_s,
        )

    def _task_callback(self, *args, **kwargs):
        """Update the status from the callback."""
        status = kwargs.get("status", None)
        if status:
            if status == TaskStatus.COMPLETED:
                self._status = FannedOutCommandStatus.COMPLETED
            if status in (TaskStatus.FAILED, TaskStatus.ABORTED, TaskStatus.NOT_FOUND):
                self._status = FannedOutCommandStatus.FAILED
            if status in (TaskStatus.QUEUED, TaskStatus.STAGING, TaskStatus.IN_PROGRESS):
                self._status = FannedOutCommandStatus.IN_PROGRESS

    def execute(self, task_callback) -> None:
        """Execute the command."""
        self._status = FannedOutCommandStatus.IN_PROGRESS
        self.start_time = time.time()
        self.command_args = list(self.command_args)
        self.command_args.insert(0, self._task_callback)
        try:
            self.logger.debug(
                (
                    f"Executing {self.command_name} with args {self.command_args} "
                    f"and kwargs. {self.command_kwargs}"
                )
            )
            res = self.command(*self.command_args, **self.command_kwargs)
            self.logger.debug(f"Result: {res}")
            self.executed_cmd_response = res
        except Exception as e:
            self.logger.exception(f"FannedOutCommand '{self.command_name}' failed to execute: {e}")
            self._status = FannedOutCommandStatus.FAILED
            self.executed_cmd_response = f"{e}"


class DishManagerCMMethodResultCode(FannedOutCommand):
    """Class that executes the method, args and kwargs passed to it.

    This class specifically handles the case where method responds with a ResultCode immediately.
    """

    def __init__(
        self,
        logger,
        method,
        component_state,
        command_args=(),
        command_kwargs={},
        awaited_component_state={},
        timeout_s=0,
    ):
        self.command_args = command_args
        self.command_kwargs = command_kwargs
        super().__init__(
            logger,
            "DishManager",
            str(method),
            method,
            component_state,
            None,
            awaited_component_state,
            timeout_s,
        )

    def execute(self, task_callback) -> None:
        """Execute the command."""
        self._status = FannedOutCommandStatus.IN_PROGRESS
        self.start_time = time.time()
        try:
            self.logger.debug(
                (
                    f"Executing {self.command_name} with args {self.command_args} "
                    f"and kwargs. {self.command_kwargs}"
                )
            )
            result_code, message = self.command(*self.command_args, **self.command_kwargs)
            self.logger.debug(f"Result: {result_code}, Message: {message}")
            self.executed_cmd_response = result_code
            # For DishManagerCMMethodResultCode, we expect an immediate response.
            # Any response that gets queued/aborted/etc is considered failed.
            # In those cases use another Action.
            if result_code == ResultCode.OK:
                self._status = FannedOutCommandStatus.COMPLETED
            else:
                self._status = FannedOutCommandStatus.FAILED
        except Exception as e:
            self.logger.exception(f"FannedOutCommand '{self.command_name}' failed to execute: {e}")
            self._status = FannedOutCommandStatus.FAILED
            self.executed_cmd_response = f"{e}"
