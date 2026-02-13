"""Specialization for B5DC functionality."""

import logging
from threading import Lock
from typing import Any, Callable, Optional

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
        state_update_lock: Lock,
        *args: Any,
        communication_state_callback: Optional[Callable] = None,
        component_state_callback: Optional[Callable] = None,
        **kwargs: Any,
    ):
        monitored_attr_names = (
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
        enum_conversion = {
            "rfcmpllLock": B5dcPllState,
            "rfcmFrequency": B5dcFrequency,
        }
        for attr, enum_ in enum_conversion.items():
            if attr in kwargs:
                kwargs[attr] = enum_(kwargs[attr])
        super()._update_component_state(**kwargs)
