"""Specialization for SPFRx functionality."""

import logging
import threading
from typing import Any, Callable, Optional

import tango
from ska_control_model import AdminMode, HealthState
from ska_mid_dish_utils.models.dish_enums import (
    Band,
    SPFRxCapabilityStates,
    SPFRxOperatingMode,
)

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager


class MonitorPing(threading.Thread):
    """A thread that executes SPFRx's MonitorPing command at a specified interval."""

    PING_ERROR_LOG_REPEAT = 5

    def __init__(
        self,
        logger: logging.Logger,
        interval: float,
        stop_event: threading.Event,
        device_fqdn: str,
    ):
        """Initialize the MonitorPing thread.

        :param logger: Logger to use for logging.
        :param interval: Time interval in seconds between function calls.
        :param stop_event: Event to signal when the thread should stop.
        :param device_fqdn: FQDN of the SPFRx device.
        """
        super().__init__(name="MonitorPingThread")
        self._logger = logger
        self._interval = interval
        self._stop_event = stop_event
        self._spfrx_trl = device_fqdn
        self._log_counter = 0
        self._device_proxy = None

    def run(self) -> None:
        """Execute the function at regular intervals until the stop event is set."""
        while not self._stop_event.is_set():
            self._execute_monitor_ping()
            # Wait for the next interval or until stopped
            self._stop_event.wait(self._interval)

    def _create_device_proxy(self) -> None:
        """Create the Tango DeviceProxy if not already created."""
        if self._device_proxy is None:
            try:
                self._device_proxy = tango.DeviceProxy(self._spfrx_trl)
            except tango.DevFailed:
                pass

    def _execute_monitor_ping(self) -> None:
        """Execute MonitorPing on the SPFRx controller.

        self.execute_command is not used to prevent spam logs about MonitorPing.
        """
        error_msg = {
            "type_error": f"DeviceProxy to {self._spfrx_trl} failed for MonitorPing",
            "other_errors": f"Failed to execute MonitorPing on {self._spfrx_trl}",
        }
        with tango.EnsureOmniThread():
            self._create_device_proxy()
            try:
                self._device_proxy.command_inout("MonitorPing", None)  # type: ignore
            except Exception:
                if self._log_counter < self.PING_ERROR_LOG_REPEAT:
                    if self._device_proxy is None:
                        self._logger.error(error_msg["type_error"])
                    else:
                        self._logger.error(error_msg["other_errors"])
                    self._log_counter += 1


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
            "dataFiberCheck",
            "configuredBand",
            "healthState",
            "b1CapabilityState",
            "b2CapabilityState",
            "b3CapabilityState",
            "b4CapabilityState",
            "b5aCapabilityState",
            "b5bCapabilityState",
            "kValue",
            "noisediodemode",
            "periodicnoisediodepars",
            "pseudorandomnoisediodepars",
            # "adminMode", TODO: Wait for SPFRx to implement adminMode
            "attenuation1polhx",
            "attenuation1polvy",
            "attenuation2polhx",
            "attenuation2polvy",
            "attenuationpolhx",
            "attenuationpolvy",
            "isklocked",
            "spectralinversion",
        )

        super().__init__(
            tango_device_fqdn,
            logger,
            monitored_attr_names,
            *args,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            quality_monitored_attributes=(
                "attenuation1polhx",
                "attenuation1polvy",
                "attenuation2polhx",
                "attenuation2polvy",
                "attenuationpolhx",
                "attenuationpolvy",
                "noisediodemode",
            ),
            **kwargs,
        )
        self._monitor_ping_thread: Optional[MonitorPing] = None
        self._communication_state_lock = state_update_lock
        self._component_state_lock = state_update_lock
        self._ping_thread_stop_event = threading.Event()

    def _stop_ping_thread(self) -> None:
        """Stop the periodic MonitorPing thread if it is running."""
        if self._monitor_ping_thread and self._monitor_ping_thread.is_alive():
            self._ping_thread_stop_event.set()
            self._monitor_ping_thread.join()

        # Clean up
        self._ping_thread_stop_event.clear()
        self._monitor_ping_thread = None

    def _start_ping_thread(self) -> None:
        """Start the MonitorPing thread."""
        self._stop_ping_thread()  # Ensure any existing ping thread is stopped

        self._monitor_ping_thread = MonitorPing(
            self.logger,
            self._MONITOR_PING_INTERVAL,
            self._ping_thread_stop_event,
            self._tango_device_fqdn,
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
            "adminmode": AdminMode,
        }
        for attr, enum_ in enum_conversion.items():
            if attr in kwargs:
                try:
                    kwargs[attr] = enum_(kwargs[attr])
                except ValueError:
                    self.logger.warning(f"Invalid value for {attr} during enum conversion.")
        super()._update_component_state(**kwargs)

    def start_communicating(self) -> None:
        """Start communication and initiate the periodic ping."""
        super().start_communicating()

        self.logger.debug("Starting MonitorPing thread.")
        self._start_ping_thread()

    def stop_communicating(self) -> None:
        """Stop communication and stop the periodic ping."""
        self.logger.debug("Stopping MonitorPing thread.")
        self._stop_ping_thread()

        super().stop_communicating()
