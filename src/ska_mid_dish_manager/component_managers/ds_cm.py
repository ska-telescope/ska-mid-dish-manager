"""Specialization for DS functionality."""

import logging
from threading import Lock
from typing import Any, Callable, Optional, Tuple

import tango
from ska_control_model import HealthState, ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager
from ska_mid_dish_manager.models.dish_enums import (
    DSOperatingMode,
    DSPowerState,
    IndexerPosition,
    PointingState,
)
from ska_mid_dish_manager.utils.decorators import check_communicating


class DSComponentManager(TangoDeviceComponentManager):
    """Specialization for DS functionality."""

    def __init__(
        self,
        tango_device_fqdn: Any,
        logger: logging.Logger,
        state_update_lock: Lock,
        *args: Any,
        communication_state_callback: Optional[Callable] = None,
        component_state_callback: Optional[Callable] = None,
        **kwargs: Any,
    ):
        monitored_attr_names = (
            "operatingMode",
            "powerState",
            "healthState",
            "pointingState",
            "indexerPosition",
            "desiredPointingAz",
            "desiredPointingEl",
            "achievedPointing",
            "band0PointingModelParams",
            "band1PointingModelParams",
            "band2PointingModelParams",
            "band3PointingModelParams",
            "band4PointingModelParams",
            "band5aPointingModelParams",
            "band5bPointingModelParams",
            "trackInterpolationMode",
            "achievedTargetLock",
            "dscCmdAuth",
            "configureTargetLock",
            "actStaticOffsetValueXel",
            "actStaticOffsetValueEl",
            "dscpowerlimitkw",
            "trackTableCurrentIndex",
            "trackTableEndIndex",
            "dscCtrlState",
        )
        super().__init__(
            tango_device_fqdn,
            logger,
            monitored_attr_names,
            *args,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            **kwargs,
        )
        self._communication_state_lock = state_update_lock
        self._component_state_lock = state_update_lock

    def _update_component_state(self, **kwargs) -> None:  # type: ignore
        """Update the int we get from the event to the Enum."""
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

    @check_communicating
    def execute_command(self, command_name: str, command_arg: Any) -> Tuple[TaskStatus, str]:
        """Check the connection and execute the command on DS manager."""
        self.logger.debug(
            "About to execute command [%s] on device [%s] with param [%s]",
            command_name,
            self._tango_device_fqdn,
            command_arg,
        )
        device_proxy = self._device_proxy_factory(self._tango_device_fqdn)
        with tango.EnsureOmniThread():
            try:
                reply = device_proxy.command_inout(command_name, command_arg)
            except tango.DevFailed as err:
                err_description = "".join([str(arg.desc) for arg in err.args])
                self.logger.error(
                    "Encountered an error executing [%s] with arg [%s] on [%s]: %s",
                    command_name,
                    command_arg,
                    self._tango_device_fqdn,
                    err_description,
                )
                return TaskStatus.FAILED, err_description
        if not isinstance(reply, (list, tuple)):
            return TaskStatus.IN_PROGRESS, reply

        [[result_code], [msg]] = reply
        if ResultCode(result_code) == ResultCode.FAILED:
            self.logger.error(
                "[%s] on [%s] failed with message: %s",
                command_name,
                self._tango_device_fqdn,
                msg,
            )
            return TaskStatus.FAILED, msg
        return TaskStatus.IN_PROGRESS, msg

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
