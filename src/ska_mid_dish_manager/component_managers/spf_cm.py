"""Specialization for SPF functionality"""
import logging
from threading import Lock
from typing import Any, AnyStr, Callable, Optional

from ska_control_model import HealthState

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager
from ska_mid_dish_manager.models.dish_enums import (
    SPFBandInFocus,
    SPFCapabilityStates,
    SPFOperatingMode,
    SPFPowerState,
)


#  pylint: disable=missing-function-docstring, invalid-name, signature-differs
class SPFComponentManager(TangoDeviceComponentManager):
    """Specialization for SPF functionality"""

    def __init__(
        self,
        tango_device_fqdn: AnyStr,
        logger: logging.Logger,
        state_update_lock: Lock,
        *args,
        communication_state_callback: Optional[Callable] = None,
        component_state_callback: Optional[Callable] = None,
        **kwargs
    ):
        self._monitored_attr_names = [
            "operatingMode",
            "powerState",
            "healthState",
            "bandInFocus",
            "b1CapabilityState",
            "b2CapabilityState",
            "b3CapabilityState",
            "b4CapabilityState",
            "b5aCapabilityState",
            "b5bCapabilityState",
        ]
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
            "operatingmode": SPFOperatingMode,
            "powerstate": SPFPowerState,
            "healthstate": HealthState,
            "bandinfocus": SPFBandInFocus,
            "b1capabilitystate": SPFCapabilityStates,
            "b2capabilitystate": SPFCapabilityStates,
            "b3capabilitystate": SPFCapabilityStates,
            "b4capabilitystate": SPFCapabilityStates,
            "b5acapabilitystate": SPFCapabilityStates,
            "b5bcapabilitystate": SPFCapabilityStates,
        }
        for attr, enum_ in enum_conversion.items():
            if attr in kwargs:
                kwargs[attr] = enum_(kwargs[attr])

        super()._update_component_state(**kwargs)

    # pylint: disable=missing-function-docstring, invalid-name
    def on(self, task_callback: Callable = None):
        raise NotImplementedError

    # pylint: disable=missing-function-docstring
    def off(self, task_callback: Callable = None):
        raise NotImplementedError

    # pylint: disable=missing-function-docstring
    def reset(self, task_callback: Callable = None):
        raise NotImplementedError

    # pylint: disable=missing-function-docstring
    def standby(self, task_callback: Callable = None):
        raise NotImplementedError
