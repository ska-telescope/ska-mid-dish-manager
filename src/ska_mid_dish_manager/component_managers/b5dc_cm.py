"""Specialization for B5DC functionality."""

import logging
from typing import Any, Callable, Optional, Tuple

import tango
from ska_control_model import CommunicationStatus, ResultCode, TaskStatus
from ska_mid_dish_dcp_lib.device.b5dc_device_mappings import (
    B5dcFrequency,
    B5dcPllState,
)

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager


class B5DCComponentManager(TangoDeviceComponentManager):
    """Specialization for B5DC functionality."""

    def __init__(
        self,
        tango_device_fqdn: Any,
        logger: logging.Logger,
        *args: Any,
        communication_state_callback: Optional[Callable] = None,
        component_state_callback: Optional[Callable] = None,
        **kwargs: Any,
    ):
        monitored_attr_names = (
            "buildState",
            "rfcmHAttenuation",
            "rfcmVAttenuation",
            "rfcmFrequency",
            "rfcmPllLock",
            "clkPhotodiodeCurrent",
            "rfTemperature",
            "rfcmPsuPcbTemperature",
            "hPolRfPowerIn",
            "hPolRfPowerOut",
            "vPolRfPowerIn",
            "vPolRfPowerOut",
            "connectionState",
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

    def _update_component_state(self, **kwargs) -> None:
        enum_conversion = {
            "rfcmpllLock": B5dcPllState,
            "rfcmFrequency": B5dcFrequency,
        }
        for attr, enum_ in enum_conversion.items():
            if attr in kwargs:
                kwargs[attr] = enum_(kwargs[attr])
        super()._update_component_state(**kwargs)

    def _update_communication_state(self, communication_state: CommunicationStatus) -> None:
        """Update b5dcServerConnectionState if connection to b5dc proxy is lost."""
        super()._update_communication_state(communication_state)

        if self._communication_state in [
            CommunicationStatus.NOT_ESTABLISHED,
            CommunicationStatus.DISABLED,
        ]:
            # If the connection to B5dc Proxy is NOT_ESTABLISHED or DISABLED then update
            # the b5dcServerConnectionState component state/attribute to match
            self._update_component_state(connectionstate=self._communication_state)
        else:
            # Manually fetch the connectionState off the B5dc Proxy device to ensure
            # the dish manager attribute is in sync with the B5dc Proxy
            try:
                on_dev_connection_state = self.read_attribute_value("connectionState")
                self._update_component_state(connectionstate=on_dev_connection_state)
            except tango.DevFailed:
                self.logger.warning("Failed to read and synchronize B5dc server connectionState")

    def _interpret_command_reply(self, command_name: str, reply: Any) -> Tuple[TaskStatus, Any]:
        """Override default interpretation to handle B5DC specific reply format."""
        # on this method evocation the reply from B5DC is of type DevVarLongStringArray
        [[result_code], [msg]] = reply
        if result_code in [ResultCode.FAILED, ResultCode.REJECTED]:
            self.logger.error(
                "[%s] on [%s] failed with message: %s",
                command_name,
                self._tango_device_fqdn,
                msg,
            )

            status_map = {
                ResultCode.FAILED: TaskStatus.FAILED,
                ResultCode.REJECTED: TaskStatus.REJECTED,
            }

            return status_map[result_code], msg
        return TaskStatus.IN_PROGRESS, msg
