"""Specialization for AP Manager functionality."""

import logging
from threading import Lock
from typing import Any, Callable, Optional, override

from ska_control_model import CommunicationStatus, HealthState
from ska_control_model.future import ControlMode

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager
from ska_mid_dish_manager.models.dish_enums import (
    DSOperatingMode,
    DSPowerState,
    IndexerPosition,
    PointingState,
)


class APComponentManager(TangoDeviceComponentManager):
    """Specialization for AP Manager functionality."""

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
        # The following is a set of attrs, usually writable on the
        # DS Manager, that cannot be written on the AP Manager
        self.unwritable_dsm_attrs = set(
            [
                "trackInterpolationMode",
            ]
        )

        monitored_attr_names: tuple[str, ...] = (
            "buildState",
            "operatingMode",
            "powerState",
            "healthState",
            "healthInfo",
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
            "dscErrorStatus",
            "dscWarningStatus",
            "dscSafetyStatus",
        )

        quality_monitored_attrs: tuple[str, ...] = (
            "buildState",
            "operatingMode",
            "powerState",
            "healthState",
            "healthInfo",
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
            "actStaticOffsetValueXel",
            "actStaticOffsetValueEl",
            "dscpowerlimitkw",
            "trackTableCurrentIndex",
            "trackTableEndIndex",
            "dscCtrlState",
            "connectionState",
            "dscErrorStatus",
            "dscWarningStatus",
            "dscSafetyStatus",
        )

        super().__init__(
            tango_device_fqdn,
            logger,
            monitored_attr_names,
            *args,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            quality_monitored_attributes=quality_monitored_attrs,
            **kwargs,
        )
        self._communication_state_lock = state_update_lock
        self._component_state_lock = state_update_lock

    def _update_component_state(self, **kwargs) -> None:
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

    @override
    def write_attribute_value(self, attribute_name: str, attribute_value: Any) -> None:
        """Call the appropriate write command or do nothing if AP Man attr write not possible."""
        if attribute_name in self.unwritable_dsm_attrs:
            write_unavailable_msg = f"Attribute [{attribute_name}] cannot be written whilst "
            "monitoring and controlling an AP Manager instance."
            self.logger.warning(write_unavailable_msg)
        else:
            return super().write_attribute_value(attribute_name, attribute_value)

    @override
    def _update_communication_state(self, communication_state: CommunicationStatus) -> None:
        """Set AP Manager controlMode on every transition into ESTABLISHED.

        On every transition from another communicationState to state ESTABLISHED
        request the controlMode of the AP Manager to go to MONITOR_AND_CONTROL to
        enable monitoring of the under AP server
        """
        prev_comm_state = self.communication_state
        super()._update_communication_state(communication_state)

        if (
            communication_state != CommunicationStatus.ESTABLISHED
            or prev_comm_state == CommunicationStatus.ESTABLISHED
        ):
            return

        try:
            self.write_attribute_value(
                "controlMode",
                ControlMode.MONITOR_AND_CONTROL,
            )
        except Exception:
            self.logger.exception("Failed to set AP Manager controlMode to MONITOR_AND_CONTROL")

    @override
    def stop_communicating(self) -> None:
        """Stop the AP server monitoring on call to stop communicating.

        DishManager sets the communicationState to DISABLED before this
        method is executed which would ordinarily prevent attr writes, therefore,
        this method bypasses the check_communicating decorator.
        """
        if not self._dp_factory_signal.is_set():
            try:
                self._write_attribute_value(
                    "controlMode",
                    ControlMode.NO_MONITOR_NO_CONTROL,
                )
            except Exception:
                self.logger.exception(
                    "Failed to set AP Manager controlMode to NO_MONITOR_NO_CONTROL"
                )

        super().stop_communicating()
