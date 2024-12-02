"""Specialization for SPFRx functionality"""

import logging
from threading import Lock
from typing import Any, Callable

import tango
from ska_control_model import CommunicationStatus, HealthState

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
        monitored_attr_names = (
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
            "noisediodemode",
            "periodicnoisediodepars",
            "pseudorandomnoisediodepars",
        )
        super().__init__(
            tango_device_fqdn,
            logger,
            monitored_attr_names,
            *args,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            quality_monitored_attributes=(
                "attenuationpolv",
                "attenuationpolh",
            ),
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
                build_state = self.read_attribute_value("swVersions")
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
