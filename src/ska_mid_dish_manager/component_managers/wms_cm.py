"""Specialization for WMS functionality."""

import logging
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, List, Optional

import tango
from ska_control_model import AdminMode, CommunicationStatus
from ska_tango_base.base import BaseComponentManager

GROUP_REQUEST_TIMEOUT_MS = 3000


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
        wind_gust_period: Optional[float] = 3.0,
        **kwargs: Any,
    ):
        self.logger = logger
        self._wms_device_names = wms_device_names
        self._wms_devices_count = len(wms_device_names)
        self._wms_polling_period = wms_polling_period
        self._wind_speed_moving_average_period = wind_speed_moving_average_period
        self._wind_gust_period = wind_gust_period

        self._wms_device_group = tango.Group("wms_devices")

        # Determine the max buffer length. Once the buffer is full we will have enough data
        # points to determine the mean wind speed and wind gust values
        self._wind_speed_buffer_length = int(
            self._wms_devices_count
            * (self._wind_speed_moving_average_period / self._wms_polling_period)
        )
        self._wind_gust_buffer_length = int(self._wind_gust_period / self._wms_polling_period)

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

        if not self._wms_device_names:
            self.logger.warning(
                "WMS component manager instantiated without any WMS device names provided."
            )
            return
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)

        self._stop_monitoring_flag.clear()

        self._wms_device_group.add(self._wms_device_names, timeout_ms=GROUP_REQUEST_TIMEOUT_MS)

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
        self._polling_start_timestamp = time.time()
        while not self._stop_monitoring_flag.wait(timeout=self._wms_polling_period):
            try:
                wind_speed_data_list = self.read_wms_group_attribute_value("wind_speed")

                _current_time = wind_speed_data_list[0][0]
                _elapsed_polling_time = _current_time - self._polling_start_timestamp

                mws = self._compute_mean_wind_speed(
                    wind_speed_data_list,
                    _current_time,
                    _elapsed_polling_time,
                )

                wg = self._process_wind_gust(
                    wind_speed_data_list,
                    _current_time,
                    _elapsed_polling_time,
                )

                self._update_component_state(
                    meanwindspeed=mws,
                    windgust=wg,
                )
            except (RuntimeError, tango.DevFailed):
                pass
            except IndexError as err:
                # Raised by processing on an empty list, in the event of a read failure
                self.logger.error(
                    f"Exception raised on processing windspeed data: {err}. "
                    "Windspeed list may be empty indicating a read failure."
                )

    def _compute_mean_wind_speed(self, wind_speed_data, current_time, elapsed_time) -> Any:
        """Calculate the mean wind speed and update the component state."""
        _mean_wind_speed = None
        self._wind_speed_buffer.extend(wind_speed_data)

        if elapsed_time >= self._wind_speed_moving_average_period:
            self._prune_stale_windspeed_data(
                current_time,
                self._wind_speed_moving_average_period,
                self._wind_speed_buffer,
            )
            _mean_wind_speed = sum(ws[1] for ws in self._wind_speed_buffer) / len(
                self._wind_speed_buffer
            )

        return _mean_wind_speed

    def _process_wind_gust(self, wind_speed_data_list, current_time, elapsed_time) -> None:
        """Determine wind gust from maximum instantaneous wind speed in the buffer."""
        # Traverse windspeed list, getting the index of the maximum
        # instantaneous windspeed value to pass for wind gust processing
        if len(wind_speed_data_list) > 1:
            inst_ws = []
            for ws in wind_speed_data_list:
                inst_ws.append(ws[1])
            max_inst_ws_index = inst_ws.index(max(inst_ws))
            self._wind_gust_buffer.append(wind_speed_data_list[max_inst_ws_index])
        else:
            self._wind_gust_buffer.append(wind_speed_data_list[0])

        _wind_gust = None

        if elapsed_time >= self._wind_gust_period:
            self._prune_stale_windspeed_data(
                current_time,
                self._wind_gust_period,
                self._wind_gust_buffer,
            )
            _wind_gust = max(ws[1] for ws in self._wind_gust_buffer)

        return _wind_gust

    def _prune_stale_windspeed_data(
        self, current_time, computation_window_period, wind_speed_buffer
    ) -> None:
        """Remove stale windspeed data points from the wind speed data buffer."""
        _data_point_expiry_time = current_time - computation_window_period
        # wind_speed_buffer[0][0] represents the timestamp of the oldest buffer datapoint
        while wind_speed_buffer and (wind_speed_buffer[0][0] < _data_point_expiry_time):
            wind_speed_buffer.popleft()

    def read_wms_group_attribute_value(self, attribute_name: str) -> Any:
        """Return list of lists containing group attr read values with timestamp."""
        reply_values = []
        try:
            grp_reply = self._wms_device_group.read_attribute(attribute_name)
            reply_timestamp = time.time()
            for reply in grp_reply:
                if reply.has_failed():
                    err_msg = (
                        f"Failed to read attribute [{attribute_name}] "
                        f"on device [{reply.dev_name()}] of "
                        f"group [{self._wms_device_group.get_name()}]",
                    )
                    self.logger.error(err_msg)
                    raise RuntimeError(err_msg)
                reply_values.append([reply_timestamp, reply.get_data().value])
        except tango.DevFailed as err:
            self.logger.error(
                "Exception raised on attempt to "
                f"read attribute [{attribute_name}] "
                f"of group [{self._wms_device_group.get_name()}]: {err}",
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
                        f"Failed to write attribute [{attribute_name}] "
                        f"on device [{reply.dev_name()}] of "
                        f"group [{self._wms_device_group.get_name()}]",
                    )
                    self.logger.error(err_msg)
                    raise RuntimeError(err_msg)
        except tango.DevFailed as err:
            self.logger.error(
                "Exception raised on attempt to "
                f"write attribute [{attribute_name}] "
                f"of group [{self._wms_device_group.get_name()}]: {err}",
            )
            raise

    def _update_component_state(self, **component_state):
        """Send updates with values."""
        # remove None values from component state update
        new_component_state = {
            wind_param: average
            for wind_param, average in component_state.items()
            if average is not None
        }
        super()._update_component_state(**new_component_state)
