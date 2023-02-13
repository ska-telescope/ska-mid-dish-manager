"""Specialization for SPFRx functionality"""
import logging
from typing import Any, AnyStr, Callable, Union

from ska_control_model import HealthState

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager
from ska_mid_dish_manager.models.dish_enums import Band, SPFRxCapabilityStates, SPFRxOperatingMode


# pylint: disable=invalid-name, missing-function-docstring, signature-differs
class SPFRxComponentManager(TangoDeviceComponentManager):
    """Specialization for SPFRx functionality"""

    def __init__(
        self,
        tango_device_fqdn: AnyStr,
        logger: logging.Logger,
        *args: Any,
        communication_state_callback: Union[Any, None] = None,
        component_state_callback: Union[Any, None] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            tango_device_fqdn,
            logger,
            *args,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            **kwargs,
        )
        self._monitored_attr_names = [
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
        ]
        for mon_attr in self._monitored_attr_names:
            self.monitor_attribute(mon_attr)

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

    # pylint: disable=missing-function-docstring, invalid-name
    def on(self, task_callback: Callable) -> Any:  # type: ignore
        raise NotImplementedError

    # pylint: disable=missing-function-docstring
    def off(self, task_callback: Callable) -> Any:  # type: ignore
        raise NotImplementedError

    # pylint: disable=missing-function-docstring
    def reset(self, task_callback: Callable) -> Any:  # type: ignore
        raise NotImplementedError

    # pylint: disable=missing-function-docstring
    def standby(self, task_callback: Callable) -> Any:  # type: ignore
        raise NotImplementedError
