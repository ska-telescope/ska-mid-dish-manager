"""Specialization for B5DC functionality."""

import logging
from threading import Lock
from typing import Any, Callable, Optional

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager
from ska_mid_dish_manager.models.dish_enums import (
    B5dcPllState,
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
            "rfcmHAttenuation",
            "rfcmVAttenuation",
            "rfcmFrequency",
            "rfcmPllLock",
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

    def _update_component_state(self, **kwargs) -> None:  # type: ignore
        enum_conversion = {
            "rfcmpllLock": B5dcPllState,
        }
        for attr, enum_ in enum_conversion.items():
            if attr in kwargs:
                kwargs[attr] = enum_(kwargs[attr])
        super()._update_component_state(**kwargs)

    # def _update_communication_state(self, communication_state: CommunicationStatus) -> None:
    #     if (self._communication_state is CommunicationStatus.ESTABLISHED) and (
    #         communication_state is CommunicationStatus.NOT_ESTABLISHED
    #     ):
    #         # Reset flag to ensure buildState is fetched the next time a server
    #         # connection is established
    #         self.build_state_fetched = False
    #     super()._update_communication_state(communication_state)

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
