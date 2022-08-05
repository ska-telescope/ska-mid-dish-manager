"""Specialization for SPF functionality"""
import logging
from typing import AnyStr, Callable, Optional

from ska_mid_dish_manager.component_managers.tango_device_cm import (
    TangoDeviceComponentManager,
)
from ska_mid_dish_manager.models.dish_enums import (
    HealthState,
    SPFOperatingMode,
    SPFPowerState,
)


class SPFComponentManager(TangoDeviceComponentManager):
    """Specialization for SPF functionality"""

    def __init__(
        self,
        tango_device_fqdn: AnyStr,
        logger: logging.Logger,
        *args,
        communication_state_callback: Optional[Callable] = None,
        component_state_callback: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(
            tango_device_fqdn,
            logger,
            *args,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            **kwargs
        )
        self._monitored_attr_names = [
            "operatingMode",
            "powerState",
            "healthState",
        ]
        for mon_attr in self._monitored_attr_names:
            self.monitor_attribute(mon_attr)

    def _update_component_state(self, **kwargs):
        """Update the int we get from the event to the Enum"""
        if "operatingmode" in kwargs:
            if (
                isinstance(kwargs["operatingmode"], str)
                and kwargs["operatingmode"].isdigit()
            ):
                kwargs["operatingmode"] = int(kwargs["operatingmode"])
            kwargs["operatingmode"] = SPFOperatingMode(kwargs["operatingmode"])
        if "powerstate" in kwargs:
            if (
                isinstance(kwargs["powerstate"], str)
                and kwargs["powerstate"].isdigit()
            ):
                kwargs["powerstate"] = int(kwargs["powerstate"])
            kwargs["powerstate"] = SPFPowerState(kwargs["powerstate"])
        if "healthstate" in kwargs:
            if (
                isinstance(kwargs["healthstate"], str)
                and kwargs["healthstate"].isdigit()
            ):
                kwargs["healthstate"] = int(kwargs["healthstate"])
            kwargs["healthstate"] = HealthState(kwargs["healthstate"])
        super()._update_component_state(**kwargs)

    # pylint: disable=missing-function-docstring, invalid-name
    def on(self, task_callback: Callable):
        raise NotImplementedError

    # pylint: disable=missing-function-docstring
    def off(self, task_callback: Callable):
        raise NotImplementedError

    # pylint: disable=missing-function-docstring
    def reset(self, task_callback: Callable):
        raise NotImplementedError

    # pylint: disable=missing-function-docstring
    def standby(self, task_callback: Callable):
        raise NotImplementedError
