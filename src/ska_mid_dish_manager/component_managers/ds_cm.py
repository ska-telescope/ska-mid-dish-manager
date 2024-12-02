"""Specialization for DS functionality"""

import logging
from threading import Lock
from typing import Any, Callable, Optional

import tango
from ska_control_model import CommunicationStatus, HealthState

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager
from ska_mid_dish_manager.models.dish_enums import (
    DSOperatingMode,
    DSPowerState,
    IndexerPosition,
    PointingState,
)


# pylint: disable=invalid-name, missing-function-docstring, signature-differs
class DSComponentManager(TangoDeviceComponentManager):
    """Specialization for DS functionality"""

    def __init__(
        self,
        tango_device_fqdn: Any,
        logger: logging.Logger,
        state_update_lock: Lock,
        *args: Any,
        communication_state_callback: Optional[Callable] = None,
        component_state_callback: Optional[Callable] = None,
        **kwargs: Any
    ):
        monitored_attr_names = (
            "operatingMode",
            "powerState",
            "healthState",
            "pointingState",
            "indexerPosition",
            "desiredPointingAz",
            "desiredPointingEl",
            "achievedPointing",
            "band1PointingModelParams",
            "band2PointingModelParams",
            "band3PointingModelParams",
            "band4PointingModelParams",
            "band5aPointingModelParams",
            "band5bPointingModelParams",
            "trackInterpolationMode",
            "achievedTargetLock",
            "configureTargetLock",
            "actStaticOffsetValueXel",
            "actStaticOffsetValueEl",
            "dscpowerlimitkw",
        )
        super().__init__(
            tango_device_fqdn,
            logger,
            monitored_attr_names,
            *args,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            **kwargs
        )
        self._communication_state_lock = state_update_lock
        self._component_state_lock = state_update_lock

    def _update_component_state(self, **kwargs) -> None:  # type: ignore
        """Update the int we get from the event to the Enum"""

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

    def _sync_communication_to_subscription(self, subscribed_attrs: list[str]) -> None:
        """
        Reflect status of monitored attribute subscription on communication state

        Overrides the callback from the parent class to pass build state information

        :param subscribed_attrs: the attributes with successful change event subscription
        :type subscribed_attrs: list
        """
        # save a copy of the subscribed attributes. this will be
        # evaluated by the function processing the valid events
        self._active_attr_event_subscriptions = set(subscribed_attrs)
        all_subscribed = set(self._monitored_attributes) == set(subscribed_attrs)
        if all_subscribed:
            self._update_communication_state(CommunicationStatus.ESTABLISHED)
            # send over the build state after all attributes are subscribed
            try:
                build_state = self.read_attribute_value("buildState")
            except tango.DevFailed:
                build_state = ""
            else:
                build_state = str(build_state)
            self._update_component_state(buildstate=build_state)
        else:
            self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)

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
