"""Specialization for WMS functionality."""

import logging
import math
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional

import tango
from ska_control_model import AdminMode, CommunicationStatus
from ska_tango_base.base import BaseComponentManager

GROUP_REQUEST_TIMEOUT_MS = 3000
MAX_READ_RETRIES = 2


class WMSComponentManager(BaseComponentManager):
    """Specialization for WMS functionality."""

    # TODO: Consider swapping out the BaseComponentManager
    # for the TaskExecutorComponentManager
    def __init__(
        self,
        wms_instances,
        *args: Any,
        logger: Optional[logging.Logger] = logging.getLogger(__name__),
        component_state_callback: Optional[Callable] = None,
        state_update_lock: Optional[threading.Lock] = None,
        wms_polling_period: Optional[float] = 1.0,
        wind_speed_moving_average_period: Optional[float] = 30.0,
        wind_gust_average_period: Optional[float] = 3.0,
        **kwargs: Any,
    ):
        self.logger = logger
        self._wms_instances = wms_instances
        self._wms_instance_count = len(wms_instances)
        self._wms_polling_period = wms_polling_period
        self._wind_speed_moving_average_period = wind_speed_moving_average_period
        self._wind_gust_average_period = wind_gust_average_period

        self._wms_device_group = tango.Group("wms_devices")

        # Determine the max buffer length. Once the buffer is full we will have enough data
        # points to determine the rolling average (mean wind speed)
        self._wind_speed_buffer_length = self._wms_instance_count * (
            self._wind_speed_moving_average_period / self._wms_polling_period
        )
        self._wind_speed_buffer_length = int(
            math.ceil(self._wind_speed_buffer_length) + self._wms_instance_count
        )
        self._wind_gust_buffer_length = int(
            self._wind_gust_average_period / self._wms_polling_period
        )
        # TODO: Evaluate whether some form of protection is needed if the mean
        # and gust periods exceed the polling period

        self._wind_speed_buffer = deque(maxlen=self._wind_speed_buffer_length)
        self._wind_gust_buffer = deque(maxlen=self._wind_gust_buffer_length)

        self._wms_attr_polling_timer = threading.Timer(
            self._wms_polling_period, self._poll_wms_wind_speed_data
        )

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
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
        # Should we check for an empty list of instances here????
        self._stop_monitoring_flag.clear()

        for new_wms_instance in self._wms_instances:
            wms_device_name = "mid/wms/" + str(new_wms_instance)
            self._wms_device_group.add(wms_device_name, timeout_ms=GROUP_REQUEST_TIMEOUT_MS)

        # Create a thread to recursively attempt a write to the adminMode=ONLINE attr and once
        # the write succeeds, the callback should kick off the wms data polling
        executor = ThreadPoolExecutor(max_workers=1)
        _wms_activated_future = executor.submit(self._activate_wms_devices)
        _wms_activated_future.add_done_callback(self._wms_communication_established)

    def _activate_wms_devices(self) -> None:
        """Start WMS monitoring of weather station servers."""
        while not self._stop_monitoring_flag.is_set():
            try:
                self.write_wms_group_attribute_value("adminMode", AdminMode.ONLINE)
                break
            except tango.DevFailed:
                self.logger.error(
                    "Failed to set WMS device(s) adminMode to ONLINE. One or more"
                    " WMS device(s) may be unavailable. Retrying"
                )
                self._stop_monitoring_flag.wait(timeout=1)

    def _wms_communication_established(self, *args) -> None:
        """Set communication state established and begin attr polling."""
        if self._stop_monitoring_flag.is_set():
            return
        self._update_communication_state(CommunicationStatus.ESTABLISHED)
        self._poll_wms_wind_speed_data()

    def stop_communicating(self) -> None:
        """Stop WMS attr polling and clean up windspeed data buffer."""
        if self._wms_attr_polling_timer.is_alive():
            self._wms_attr_polling_timer.cancel()

        self._stop_monitoring_flag.set()

        self._wind_speed_buffer.clear()

        try:
            self.write_wms_group_attribute_value("adminMode", AdminMode.OFFLINE)
            self._wms_device_group.remove_all()
        except tango.DevFailed:
            self.logger.error(
                "Failed to set WMS device(s) adminMode to OFFLINE. "
                "One or more WMS device(s) may be unavailable"
            )
        self._update_communication_state(CommunicationStatus.DISABLED)

    def _restart_polling_timer(self) -> None:
        """Cancel any old instances of the WMS polling timer and start new instance."""
        if self._wms_attr_polling_timer.is_alive():
            self._wms_attr_polling_timer.cancel()
        self._wms_attr_polling_timer = threading.Timer(
            self._wms_polling_period,
            self._poll_wms_wind_speed_data,
        )
        self._wms_attr_polling_timer.start()

    def _poll_wms_wind_speed_data(self):
        """Fetch WMS windspeed data and publish it to the rolling avg calc."""
        retry_count = 0
        while retry_count <= MAX_READ_RETRIES:
            try:
                wind_speed_list = self.read_wms_group_attribute_value("wind_speed")
                wind_speed_list.sort()
                # Pass only the largest wind speed value to wind gust buffer
                self._process_wind_gust(wind_speed_list[-1])
                self._compute_mean_wind_speed(wind_speed_list)
                self._update_communication_state(CommunicationStatus.ESTABLISHED)
                break
            except (Exception, tango.DevFailed):
                retry_count += 1
                if retry_count > MAX_READ_RETRIES:
                    self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
                self._stop_monitoring_flag.wait(1)

        self._restart_polling_timer()

    def _compute_mean_wind_speed(self, wind_speed_data) -> None:
        """Calculate the mean wind speed and update the component state."""
        self._wind_speed_buffer.extendleft(wind_speed_data)

        if len(self._wind_speed_buffer) == self._wind_speed_buffer_length:
            _mean_wind_speed = sum(self._wind_speed_buffer) / self._wind_speed_buffer_length
            self._update_component_state(meanwindspeed=_mean_wind_speed)

    def _process_wind_gust(self, max_instantaneous_wind_speed) -> None:
        """Determine wind gust from maximum instantaneous wind speed in the buffer."""
        self._wind_gust_buffer.extendleft(max_instantaneous_wind_speed)

        if len(self._wind_gust_buffer) == self._wind_gust_buffer_length:
            _wind_gust_avg = sum(self._wind_gust_buffer) / self._wind_gust_buffer_length
            self._update_component_state(windgust=_wind_gust_avg)

    def read_wms_group_attribute_value(self, attribute_name: str) -> Any:
        """Return list of group attributes."""
        self.logger.debug(
            "About to read attribute [%s] on group [%s] containing [%s]",
            attribute_name,
            self._wms_device_group.get_name(),
            self._wms_device_group.get_device_list(),
        )
        reply_values = []
        try:
            grp_reply = self._wms_device_group.read_attribute(attribute_name)
            for reply in grp_reply:
                if reply.has_failed():
                    self.logger.error(
                        "Failed to read attribute [%s] on device [%s] of group [%s]",
                        attribute_name,
                        reply.dev_name(),
                        self._wms_device_group.get_name(),
                    )
                    raise Exception
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
        self.logger.debug(
            "About to write attribute [%s] on group [%s] containing [%s]",
            attribute_name,
            self._wms_device_group.get_name(),
            self._wms_device_group.get_device_list(),
        )
        try:
            grp_reply = self._wms_device_group.write_attribute(attribute_name, attribute_value)
            for reply in grp_reply:
                if reply.has_failed():
                    self.logger.error(
                        "Failed to write attribute [%s] on device [%s] of group [%s]",
                        attribute_name,
                        reply.dev_name(),
                        self._wms_device_group.get_name(),
                    )
                    raise Exception
        except tango.DevFailed:
            self.logger.error(
                "Exception raised on attempt to write attribute [%s] of group [%s].",
                attribute_name,
                self._wms_device_group.get_name(),
            )
            raise
