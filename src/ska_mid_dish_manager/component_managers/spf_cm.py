"""Specialization for SPF functionality"""
import logging
from typing import AnyStr, Callable, Optional

from ska_mid_dish_manager.component_managers.tango_device_cm import (
    TangoDeviceComponentManager,
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
        self.monitor_attribute("operatingMode")
        self.monitor_attribute("powerState")
        self.monitor_attribute("healthState")

    def on(self, task_callback: Callable):
        raise NotImplementedError

    def off(self, task_callback: Callable):
        raise NotImplementedError

    def reset(self, task_callback: Callable):
        raise NotImplementedError

    def standby(self, task_callback: Callable):
        raise NotImplementedError
