"""Specialization for DS functionality."""

import logging
from threading import Lock
from typing import Any, Callable, Optional, Tuple

from ska_control_model import CommunicationStatus, HealthState, ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager
from ska_mid_dish_manager.models.constants import DS_ERROR_STATUS_ATTRIBUTES
from ska_mid_dish_manager.models.dish_enums import (
    DSOperatingMode,
    DSPowerState,
    IndexerPosition,
    PointingState,
)


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
        monitored_attr_names: tuple[str, ...] = (
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
            "connectionState",
        )

        monitored_attr_names = monitored_attr_names + tuple(DS_ERROR_STATUS_ATTRIBUTES.keys())

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

    def _update_communication_state(self, communication_state: CommunicationStatus) -> None:
        """Update dsc connection state if connection to ds is lost."""
        super()._update_communication_state(communication_state)

        if self._communication_state in [
            CommunicationStatus.NOT_ESTABLISHED,
            CommunicationStatus.DISABLED,
        ]:
            # If the connection to DSManager is NOT_ESTABLISHED or DISABLED then update
            # the dscconnectionstate to match
            self._update_component_state(connectionstate=self._communication_state)

    def _interpret_command_reply(self, command_name: str, reply: Any) -> Tuple[TaskStatus, Any]:
        """Override default interpretation to handle DS specific reply format."""
        # on this method evocation the reply from DS is of type DevVarLongStringArray
        [[result_code], [msg]] = reply
        if result_code == ResultCode.FAILED:
            self.logger.error(
                "[%s] on [%s] failed with message: %s",
                command_name,
                self._tango_device_fqdn,
                msg,
            )
            return TaskStatus.FAILED, msg
        return TaskStatus.IN_PROGRESS, msg
