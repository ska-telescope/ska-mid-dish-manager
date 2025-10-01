"""Specialization for B5DC functionality."""

import logging
from threading import Lock
from typing import Any, Callable, Optional

import logging
from typing import Any, Callable, Optional

from ska_control_model import CommunicationStatus, TaskStatus, HealthState

from ska_mid_dish_b5dc_proxy.models.constants import B5DC_BUILD_STATE_DEVICE_NAME
from 
from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager
from ska_mid_dish_manager.models.dish_enums import (
    B5DCOperatingMode,
)

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
            "adminMode",
            "buildstate",
            "rfcmHAttenuation",
            "rfcmVAttenuation",
            "rfcmPllLock",
            "rfTemperature",
            "rfcmPsuPcbTemperature",
            "healthState",
            "hPolRfPowerIn",
            "hPolRfPowerOut",
            "operatingMode",
            "powerState",
            "vPolRfPowerIn",
            "vPolRfPowerOut",
        )
        super().__init__(
            tango_device_fqdn,
            logger,
            monitored_attr_names,
            state_update_lock,
            *args,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            **kwargs,
        )
        self._communication_state_lock = state_update_lock
        self._component_state_lock = state_update_lock
    
    def _update_component_state(self, **kwargs) -> None:  # type: ignore
        enum_conversion = {
            "operatingmode": B5DCOperatingMode,
            "healthstate": HealthState,  
        }
        for attr, enum_ in enum_conversion.items():
            if attr in kwargs:
                kwargs[attr] = enum_(kwargs[attr])
            pass 
    def _update_communication_state(self, communication_state: CommunicationStatus) -> None:
        if (self._communication_state is CommunicationStatus.ESTABLISHED) and (
            communication_state is CommunicationStatus.NOT_ESTABLISHED
        ):
            # Reset flag to ensure buildState is fetched the next time a server
            # connection is established
            self.build_state_fetched = False
        super()._update_communication_state(communication_state)

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
