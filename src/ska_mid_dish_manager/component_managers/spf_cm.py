"""Specialization for SPF functionality."""

import logging
from threading import Lock
from typing import Any, Callable, Optional

from ska_control_model import HealthState
from ska_mid_dish_utils.sim_enums import (
    SPFBandInFocus,
    SPFCapabilityStates,
    SPFOperatingMode,
    SPFPowerState,
)

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager


#  pylint: disable=missing-function-docstring, invalid-name, signature-differs
class SPFComponentManager(TangoDeviceComponentManager):
    """Specialization for SPF functionality."""

    def __init__(
        self,
        tango_device_fqdn: str,
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
            "bandInFocus",
            "b1CapabilityState",
            "b2CapabilityState",
            "b3CapabilityState",
            "b4CapabilityState",
            "b5aCapabilityState",
            "b5bCapabilityState",
            "b1LnaVPowerState",
            "b2LnaVPowerState",
            "b1LnaHPowerState",
            "b2LnaHPowerState",
            "b3LnaPowerState",
            "b4LnaPowerState",
            "b5aLnaPowerState",
            "b5bLnaPowerState",
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

    def _update_component_state(self, **kwargs: Any) -> None:
        """Update the int we get from the event to the Enum."""
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
