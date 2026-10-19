"""Specialization for AP Manager functionality."""

import logging
from threading import Lock
from typing import Any, Callable, Optional, Tuple, override

from ska_control_model import HealthState, TaskStatus

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
        # The following is a set of commands, usually fanned out to the
        # DS Manager, that are not implemented on the AP Manager
        self.unmapped_ds_manager_commands = set(
            [
                "TrackLoadStaticOff",
            ]
        )

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
    def execute_command(
        self, command_name: str, command_arg: Any, truncate_arg_in_logs: bool = False
    ) -> Tuple[TaskStatus, Any]:
        """Intercept any commands that are known not to be executable on the AP Manager."""
        if command_name in self.unmapped_ds_manager_commands:
            return (
                TaskStatus.COMPLETED,
                f"This DS Manager command [{command_name}] is not executed whilst monitoring and "
                "controlling an AP Manager instance.",
            )
        else:
            return super().execute_command(command_name, command_arg, truncate_arg_in_logs)

    @override
    def write_attribute_value(self, attribute_name: str, attribute_value: Any) -> None:
        """Call the appropriate write command or do nothing if AP Man attr write not possible."""
        if attribute_name in self.unwritable_dsm_attrs:
            write_unavailable_msg = f"Attribute [{attribute_name}] cannot be written whilst "
            "monitoring and controlling an AP Manager instance."
            self.logger.warning(write_unavailable_msg)
        else:
            return super().write_attribute_value(attribute_name, attribute_value)
