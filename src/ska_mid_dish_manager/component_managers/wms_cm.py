"""Specialization for WMS functionality."""

import logging
import math
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, List, Optional

import tango
from ska_control_model import AdminMode, CommunicationStatus
from ska_tango_base.base import BaseComponentManager

GROUP_REQUEST_TIMEOUT_MS = 3000
MAX_READ_RETRIES = 2


class WMSComponentManager(BaseComponentManager):
    """Specialization for WMS functionality."""

    def __init__(
        self,
        wms_device_names: List[str],
        *args: Any,
        logger: Optional[logging.Logger] = logging.getLogger(__name__),
        component_state_callback: Optional[Callable] = None,
        state_update_lock: Optional[threading.Lock] = None,
        wms_polling_period: Optional[float] = 1.0,
        wind_speed_moving_average_period: Optional[float] = 600.0,
        wind_gust_average_period: Optional[float] = 3.0,
        **kwargs: Any,
    ):
        self.logger = logger
        self._wms_device_names = wms_device_names
        self._wms_devices_count = len(wms_device_names)
        self._wms_polling_period = wms_polling_period
        self._wind_speed_moving_average_period = wind_speed_moving_average_period
        self._wind_gust_average_period = wind_gust_average_period

        self._wms_device_group = tango.Group("wms_devices")

        # Determine the max buffer length. Once the buffer is full we will have enough data
        # points to determine the mean wind speed and wind gust values
        self._wind_speed_buffer_length = self._wms_devices_count * (
            self._wind_speed_moving_average_period / self._wms_polling_period
        )
        self._wind_speed_buffer_length = int(
            math.ceil(self._wind_speed_buffer_length) + self._wms_devices_count
        )
        self._wind_gust_buffer_length = int(
            self._wind_gust_average_period / self._wms_polling_period
        )
        # TODO: Evaluate whether some form of protection is needed if the mean
        # and gust periods exceed the polling period

        self._wind_speed_buffer = deque(maxlen=self._wind_speed_buffer_length)
        self._wind_gust_buffer = deque(maxlen=self._wind_gust_buffer_length)

        self.executor = ThreadPoolExecutor(max_workers=1)

        self._stop_monitoring_flag = threading.Event()

        super().__init__(
            logger,
            *args,
            component_state_callback=component_state_callback,
            **kwargs,
        )
        if state_update_lock is not None:
            self._component_state_lock = state_update_lock

    def start_communicating(self) -> None:
        """Add WMS device to group and initiate WMS attr polling."""
        self.stop_communicating()

        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
        if not self._wms_device_names:
            self.logger.warning(
                "WMS component manager instantiated without any WMS device names provided."
            )
            return

        self._stop_monitoring_flag.clear()

        for device_name in self._wms_device_names:
            self._wms_device_group.add(device_name, timeout_ms=GROUP_REQUEST_TIMEOUT_MS)

        _wms_monitoring_started_future = self.executor.submit(self._start_monitoring)
        _wms_monitoring_started_future.add_done_callback(self._run_wms_group_polling)

    def _start_monitoring(self) -> None:
        """Start WMS monitoring of weather station servers."""
        while not self._stop_monitoring_flag.wait(timeout=self._wms_polling_period):
            try:
                self.write_wms_group_attribute_value("adminMode", AdminMode.ONLINE)
                self._update_communication_state(CommunicationStatus.ESTABLISHED)
                break
            except (tango.DevFailed, RuntimeError):
                self.logger.error(
                    "Failed to set WMS device(s) adminMode to ONLINE. One or more"
                    " WMS device(s) may be unavailable. Retrying"
                )

    def stop_communicating(self) -> None:
        """Stop WMS attr polling and clean up windspeed data buffer."""
        self._stop_monitoring_flag.set()

        self.executor.shutdown(wait=True, cancel_futures=True)
        self.executor = ThreadPoolExecutor(max_workers=1)

        self._wind_speed_buffer.clear()
        self._wind_gust_buffer.clear()

        try:
            self.write_wms_group_attribute_value("adminMode", AdminMode.OFFLINE)
            self._wms_device_group.remove_all()
        except (tango.DevFailed, RuntimeError):
            self.logger.error(
                "Failed to set WMS device(s) adminMode to OFFLINE. "
                "One or more WMS device(s) may be unavailable"
            )
        self._update_communication_state(CommunicationStatus.DISABLED)

    def _run_wms_group_polling(self, *args):
        """Fetch WMS windspeed data and publish it to the rolling avg calc."""
        while not self._stop_monitoring_flag.wait(timeout=self._wms_polling_period):
            try:
                wind_speed_data_list = self.read_wms_group_attribute_value("wind_speed")
                wg = self._process_wind_gust(max(wind_speed_data_list))
                mws = self._compute_mean_wind_speed(wind_speed_data_list)
                self._update_component_state(
                    meanwindspeed=mws,
                    windgust=wg,
                )
            except (RuntimeError, tango.DevFailed):
                pass
            except ValueError as err:
                # Raised by max() on an empty list
                self.logger.error(f"Exception raised on processing windspeed data: {err}")

    def _compute_mean_wind_speed(self, wind_speed_data) -> Any:
        """Calculate the mean wind speed and update the component state."""
        _mean_wind_speed = None
        self._wind_speed_buffer.extendleft(wind_speed_data)

        if len(self._wind_speed_buffer) == self._wind_speed_buffer_length:
            _mean_wind_speed = sum(self._wind_speed_buffer) / self._wind_speed_buffer_length

        return _mean_wind_speed

    def _process_wind_gust(self, max_instantaneous_wind_speed) -> None:
        """Determine wind gust from maximum instantaneous wind speed in the buffer."""
        _wind_gust = None
        self._wind_gust_buffer.append(max_instantaneous_wind_speed)

        if len(self._wind_gust_buffer) == self._wind_gust_buffer_length:
            _wind_gust = max(self._wind_gust_buffer)

        return _wind_gust

    def read_wms_group_attribute_value(self, attribute_name: str) -> Any:
        """Return list of group attributes."""
        reply_values = []
        try:
            grp_reply = self._wms_device_group.read_attribute(attribute_name)
            for reply in grp_reply:
                if reply.has_failed():
                    err_msg = (
                        "Failed to read attribute [%s] on device [%s] of group [%s]",
                        attribute_name,
                        reply.dev_name(),
                        self._wms_device_group.get_name(),
                    )
                    self.logger.error(err_msg)
                    raise RuntimeError(err_msg)
                reply_values.append(reply.get_data().value)
        except tango.DevFailed:
            self.logger.error(
                "Exception raised on attempt to read attribute [%s] of group [%s].",
                attribute_name,
                self._wms_device_group.get_name(),
            )
            raise
        return reply_values

    def write_wms_group_attribute_value(self, attribute_name: str, attribute_value: Any) -> None:
        """Write data to WMS tango group devices."""
        try:
            grp_reply = self._wms_device_group.write_attribute(attribute_name, attribute_value)
            for reply in grp_reply:
                if reply.has_failed():
                    err_msg = (
                        "Failed to write attribute [%s] on device [%s] of group [%s]",
                        attribute_name,
                        reply.dev_name(),
                        self._wms_device_group.get_name(),
                    )
                    self.logger.error(err_msg)
                    raise RuntimeError(err_msg)
        except tango.DevFailed:
            self.logger.error(
                "Exception raised on attempt to write attribute [%s] of group [%s].",
                attribute_name,
                self._wms_device_group.get_name(),
            )
            raise
