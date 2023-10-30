"""Specialization for SPFRx functionality"""
import logging
from threading import Lock
from typing import Any, Callable

from ska_control_model import HealthState, ResultCode

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager
from ska_mid_dish_manager.models.dish_enums import Band, SPFRxCapabilityStates, SPFRxOperatingMode


# pylint: disable=invalid-name, missing-function-docstring, signature-differs
class SPFRxComponentManager(TangoDeviceComponentManager):
    """Specialization for SPFRx functionality"""

    def __init__(
        self,
        tango_device_fqdn: str,
        logger: logging.Logger,
        state_update_lock: Lock,
        *args: Any,
        communication_state_callback: Any = None,
        component_state_callback: Any = None,
        **kwargs: Any
    ):
        self._monitored_attr_names = (
            "operatingMode",
            "capturingData",
            "configuredBand",
            "healthState",
            "b1CapabilityState",
            "b2CapabilityState",
            "b3CapabilityState",
            "b4CapabilityState",
            "b5aCapabilityState",
            "b5bCapabilityState",
            "attenuationPolH",
            "attenuationPolV",
            "kValue",
        )
        super().__init__(
            tango_device_fqdn,
            logger,
            self._monitored_attr_names,
            *args,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            **kwargs
        )
        self._communication_state_lock = state_update_lock
        self._component_state_lock = state_update_lock

    def _update_component_state(self, **kwargs: Any) -> None:
        """Update the int we get from the event to the Enum"""
        enum_conversion = {
            "operatingmode": SPFRxOperatingMode,
            "healthstate": HealthState,
            "configuredband": Band,
            "b1capabilitystate": SPFRxCapabilityStates,
            "b2capabilitystate": SPFRxCapabilityStates,
            "b3capabilitystate": SPFRxCapabilityStates,
            "b4capabilitystate": SPFRxCapabilityStates,
            "b5acapabilitystate": SPFRxCapabilityStates,
            "b5bcapabilitystate": SPFRxCapabilityStates,
        }
        for attr, enum_ in enum_conversion.items():
            if attr in kwargs:
                kwargs[attr] = enum_(kwargs[attr])

        super()._update_component_state(**kwargs)

    def set_kvalue(self, value):
        return (ResultCode.OK, "SetKValue sent successfully to SPFRx")

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
