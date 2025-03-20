"""Specialization for SPFRx functionality"""

import logging
import threading
from typing import Any, Callable, Optional

import tango
from ska_control_model import HealthState

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager
from ska_mid_dish_manager.models.dish_enums import Band, SPFRxCapabilityStates, SPFRxOperatingMode

# pylint: disable=invalid-name,missing-function-docstring,signature-differs,too-many-instance-attributes


class MonitorPing(threading.Thread):
    """
    A thread that executes SPFRx's MonitorPing command at a specified interval.
    """

    def __init__(
        self,
        trl: str,
        logger: logging.Logger,
        interval: float,
        function: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ):
        """
        Initialize the MonitorPing thread.

        :param trl: trl of the Tango device to monitor.
        :param logger: Logger to log messages and warnings.
        :param interval: Time interval (in seconds) between function calls.
        :param function: The function to be called periodically (MonitorPing).
        :param args: Positional arguments to pass to the function.
        :param kwargs: Keyword arguments to pass to the function.
        """
        super().__init__(name="MonitorPingThread")
        self.logger = logger
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self._trl = trl
        self._device_proxy: Optional[tango.DeviceProxy] = None
        self._stop_event = threading.Event()

    def _create_device_proxy(self) -> None:
        """Create the Tango DeviceProxy if not already created."""
        if self._device_proxy is None:
            with tango.EnsureOmniThread():
                try:
                    self._device_proxy = tango.DeviceProxy(self._trl)
                except tango.DevFailed:
                    self._device_proxy = None

    def run(self) -> None:
        """Execute the function at regular intervals until the stop event is set."""
        while not self._stop_event.is_set():
            self._create_device_proxy()
            try:
                self.function(self._device_proxy, *self.args, **self.kwargs)
            except Exception as e:  # pylint:disable=broad-except
                self.logger.warning(f"Failed to execute MonitorPing: {e}")
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
        communication_state_callback: Optional[Callable] = None,
        component_state_callback: Optional[Callable] = None,
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
        self._monitor_ping_thread: Optional[MonitorPing] = None
        self._communication_state_lock = state_update_lock
        self._component_state_lock = state_update_lock

    def _stop_ping_thread(self) -> None:
        """Stop the MonitorPing thread if it is running."""
        if self._monitor_ping_thread and self._monitor_ping_thread.is_alive():
            self._monitor_ping_thread.stop()
            self._monitor_ping_thread.join()
            self._monitor_ping_thread = None

    def _start_ping_thread(self) -> None:
        """Start the MonitorPing thread."""
        self._stop_ping_thread()  # Ensure any existing ping thread is stopped

        self._monitor_ping_thread = MonitorPing(
            self._tango_device_fqdn,
            self.logger,
            self._MONITOR_PING_INTERVAL,
            self.execute_monitor_ping,
        )
        self._monitor_ping_thread.start()

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

    def execute_monitor_ping(self, device_proxy: tango.DeviceProxy) -> None:
        """
        Execute MonitorPing on the SPFRx controller.

        self.execute_command is not used to prevent spam logs about MonitorPing.
        """
        with tango.EnsureOmniThread():
            try:
                device_proxy.command_inout("MonitorPing", None)
            except tango.DevFailed:
                self.logger.error(f"Failed to execute MonitorPing on {self._tango_device_fqdn}")

    def start_communicating(self) -> None:
        """Start communication with the SPFRx device and initiate the MonitorPing thread."""
        super().start_communicating()

        self.logger.debug("Starting MonitorPing thread.")
        self._start_ping_thread()

    def stop_communicating(self) -> None:
        """Stop communication with the SPFRx device and terminate the MonitorPing thread."""
        self.logger.debug("Stopping MonitorPing thread.")
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
