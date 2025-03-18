"""Specialization for SPFRx functionality"""

import logging
import threading
from typing import Any, Callable, Optional

import tango
from ska_control_model import HealthState

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager
from ska_mid_dish_manager.models.dish_enums import Band, SPFRxCapabilityStates, SPFRxOperatingMode

# pylint: disable=invalid-name, missing-function-docstring, signature-differs


class MonitorPing(threading.Thread):
    """
    A thread that executes SPFRx's MonitorPing command at a specified interval.
    """

    def __init__(self, interval: float, function: Callable[..., Any], *args: Any, **kwargs: Any):
        """
        Initialize the MonitorPing thread.

        :param interval: Time interval in seconds between function calls.
        :param function: The function to be called periodically.
        :param args: Positional arguments to pass to the function.
        :param kwargs: Keyword arguments to pass to the function.
        """
        super().__init__(name="MonitorPingThread")
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self._stop_event = threading.Event()

    def run(self) -> None:
        """Execute the function at regular intervals until the stop event is set."""
        while not self._stop_event.is_set():
            self.function(*self.args, **self.kwargs)
            # Wait for the next interval or until stopped
            self._stop_event.wait(self.interval)

    def stop(self) -> None:
        """Stop the periodic function execution."""
        self._stop_event.set()


class SPFRxComponentManager(TangoDeviceComponentManager):
    """Specialization for SPFRx functionality."""

    _MONITOR_PING_INTERVAL = 3  # Constant for ping interval in seconds

    def __init__(
        self,
        tango_device_fqdn: str,
        logger: logging.Logger,
        state_update_lock: threading.Lock,
        *args: Any,
        communication_state_callback: Any = None,
        component_state_callback: Any = None,
        **kwargs: Any,
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
            **kwargs,
        )
        self._periodically_ping_device: Optional[MonitorPing] = None
        self._communication_state_lock = state_update_lock
        self._component_state_lock = state_update_lock

    def _stop_ping_thread(self) -> None:
        """Stop the periodic MonitorPing thread if it is running."""
        if self._periodically_ping_device and self._periodically_ping_device.is_alive():
            self._periodically_ping_device.stop()
            self._periodically_ping_device.join()
            self._periodically_ping_device = None

    def _start_ping_thread(self) -> None:
        """Start the MonitorPing thread."""
        self._stop_ping_thread()  # Ensure any existing ping thread is stopped

        self._periodically_ping_device = MonitorPing(
            self._MONITOR_PING_INTERVAL, self.execute_monitor_ping
        )
        self._periodically_ping_device.start()

    def _update_component_state(self, **kwargs: Any) -> None:
        """Update component state with proper enum conversion."""
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
                try:
                    kwargs[attr] = enum_(kwargs[attr])
                except ValueError:
                    self.logger.warning(f"Invalid value for {attr} during enum conversion.")

        super()._update_component_state(**kwargs)

    def execute_monitor_ping(self) -> None:
        """
        Execute MonitorPing on the SPFRx controller.

        self.execute_command is not used to prevent spam logs about MonitorPing.
        """
        device_proxy = self._device_proxy_factory(self._tango_device_fqdn)
        with tango.EnsureOmniThread():
            try:
                device_proxy.command_inout("MonitorPing", None)
            except tango.DevFailed:
                self.logger.error(
                    "Failed to execute [%s] on [%s]",
                    "MonitorPing",
                    self._tango_device_fqdn,
                )

    def start_communicating(self) -> None:
        """Start communication and initiate the periodic ping."""
        super().start_communicating()
        self._start_ping_thread()

    def stop_communicating(self) -> None:
        """Stop communication and stop the periodic ping."""
        self._stop_ping_thread()
        super().stop_communicating()

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
