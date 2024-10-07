"""Specialization for DS functionality"""

import logging
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Callable, Optional

from ska_control_model import HealthState, ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager
from ska_mid_dish_manager.models.dish_enums import (
    DSOperatingMode,
    DSPowerState,
    IndexerPosition,
    PointingState,
)


# pylint: disable=invalid-name, missing-function-docstring, signature-differs
class DSComponentManager(TangoDeviceComponentManager):
    """Specialization for DS functionality"""

    def __init__(
        self,
        tango_device_fqdn: Any,
        logger: logging.Logger,
        state_update_lock: Lock,
        command_tracker,  # CommandTracker
        *args: Any,
        communication_state_callback: Optional[Callable] = None,
        component_state_callback: Optional[Callable] = None,
        **kwargs: Any,
    ):
        self._command_tracker = command_tracker
        self._monitored_attr_names = (
            "operatingMode",
            "powerState",
            "healthState",
            "pointingState",
            "indexerPosition",
            "desiredPointingAz",
            "desiredPointingEl",
            "achievedPointing",
            "band1PointingModelParams",
            "band2PointingModelParams",
            "band3PointingModelParams",
            "band4PointingModelParams",
            "band5aPointingModelParams",
            "band5bPointingModelParams",
            "trackInterpolationMode",
            "achievedTargetLock",
            "configureTargetLock",
            "actStaticOffsetValueXel",
            "actStaticOffsetValueEl",
            "longRunningCommandProgress",
            "longRunningCommandResult",
        )
        super().__init__(
            tango_device_fqdn,
            logger,
            self._monitored_attr_names,
            *args,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            **kwargs,
        )
        self._communication_state_lock = state_update_lock
        self._component_state_lock = state_update_lock

    def _update_component_state(self, **kwargs) -> None:  # type: ignore
        """Update event values before processing.

        - INT
          - Convert to the expected Enum
        - longrunningcommandprogress and longrunningcommandresult
          - Update the task status
        """

        if "longrunningcommandprogress" in kwargs:
            command_id, progress = kwargs["longrunningcommandprogress"]
            progress = "From Dish Structure Manager: " + progress
            self.logger.info(f"DS Component manager updating with progress: {progress}")
            if command_id:
                if command_id not in self._command_tracker._commands:
                    self.logger.info(f"DS Subdevice command not in command tracker on receipt of progress update {progress}. Adding")
                    self._command_tracker._commands[command_id] = {
                        "name": f"Dish Structure Manager command {command_id}",
                        "status": TaskStatus.IN_PROGRESS,
                        "progress": None,
                        "completed_callback": None,
                    }
                self._command_tracker.update_command_info(command_id, progress=progress)
            del kwargs["longrunningcommandprogress"]

        if "longrunningcommandresult" in kwargs:
            command_id, result = kwargs["longrunningcommandresult"]
            result = "From Dish Structure Manager: " + result
            self.logger.info(f"DS Component manager updating with result: {result}")
            if command_id:
                if command_id not in self._command_tracker._commands:
                    self.logger.info(f"DS Subdevice command not in command tracker on receipt of result update {result}. Adding")
                    self._command_tracker._commands[command_id] = {
                        "name": f"Dish Structure Manager command {command_id}",
                        "status": TaskStatus.IN_PROGRESS,
                        "progress": None,
                        "completed_callback": None,
                    }
                self._command_tracker.update_command_info(
                    command_id,
                    result=result,
                )
                self._command_tracker.update_command_info(
                    command_id,
                    status=TaskStatus.COMPLETED,
                )
            del kwargs["longrunningcommandresult"]
        self.logger.info(f"DS command tracker commands: {self._command_tracker._commands}")

        if not kwargs:
            return

        enum_conversion = {
            "operatingmode": DSOperatingMode,
            "powerstate": DSPowerState,
            "healthstate": HealthState,
            "pointingstate": PointingState,
            "indexerposition": IndexerPosition,
        }
        for attr, enum_ in enum_conversion.items():
            if attr in kwargs:
                kwargs[attr] = enum_(kwargs[attr])

        super()._update_component_state(**kwargs)

    # pylint: disable=missing-function-docstring, invalid-name
    def on(self, task_callback: Callable = None) -> Any:  # type: ignore
        raise NotImplementedError

    # pylint: disable=missing-function-docstring
    def off(self, task_callback: Callable = None) -> Any:  # type: ignore
        raise NotImplementedError

    # pylint: disable=missing-function-docstring
    def reset(self, task_callback: Callable = None) -> Any:  # type: ignore
        raise NotImplementedError

    # pylint: disable=missing-function-docstring
    def standby(self, task_callback: Callable = None) -> Any:  # type: ignore
        raise NotImplementedError
