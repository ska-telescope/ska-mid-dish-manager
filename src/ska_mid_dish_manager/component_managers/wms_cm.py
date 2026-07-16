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
    """Specialization for Weather Monitoring System (WMS) functionality.

    This component manager handles communication and data processing
    for a single or a group of WMS Tango device(s), providing periodic polling of
    wind speed data, calculation of mean wind speed and wind gust values,
    and management of device states.

    :param wms_device_names: List of TRLs of the WMS devices to be monitored.
    :type wms_device_names: List[str]
    :param args: Additional positional arguments passed to the base component manager.
    :type args: Any
    :param logger: Optional logger instance for logging messages.
    :type logger: Optional[logging.Logger]
    :param component_state_callback: Optional callback for component state updates.
    :type component_state_callback: Optional[Callable]
    :param state_update_lock: Optional threading lock for component state updates.
    :type state_update_lock: Optional[threading.Lock]
    :param wms_polling_period: Polling period (in seconds) for fetching wind speed
        data.
    :type wms_polling_period: Optional[float]
    :param wind_speed_moving_average_period: Time window (in seconds) over which the
        mean wind speed is calculated.
    :type wind_speed_moving_average_period: Optional[float]
    :param wind_gust_period: Time window (in seconds) over which the wind gust
        is calculated.
    :type wind_gust_period: Optional[float]
    :param kwargs: Additional keyword arguments passed to the base component manager.
    :type kwargs: Any
    """

    def __init__(
        self,
        wms_device_names: List[str],
        *args: Any,
        logger: Optional[logging.Logger] = logging.getLogger(__name__),
        component_state_callback: Optional[Callable] = None,
        communication_state_callback: Optional[Callable] = None,
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
        # points to determine the mean wind speed and wind gust values. The additions of
        # device count and 1 to the buffer lengths ensure the wind speed readings
        # of the first polling cycle are accounted for
        self._wind_speed_buffer_length = (
            int(
                self._wms_devices_count
                * (self._wind_speed_moving_average_period / self._wms_polling_period)
            )
            + self._wms_devices_count
        )
        self._wind_gust_buffer_length = int(self._wind_gust_period / self._wms_polling_period) + 1

        self._wind_speed_buffer = deque(maxlen=self._wind_speed_buffer_length)
        self._wind_gust_buffer = deque(maxlen=self._wind_gust_buffer_length)

        self.executor = ThreadPoolExecutor(max_workers=1)

        self._stop_monitoring_flag = threading.Event()

        super().__init__(
            logger,
            *args,
            component_state_callback=component_state_callback,
            communication_state_callback=communication_state_callback,
            **kwargs,
        )
        if state_update_lock is not None:
            self._component_state_lock = state_update_lock

    def start_communicating(self) -> None:
        """Add WMS device(s) to group and initiate WMS attr polling."""
        self.stop_communicating()

        if not self._wms_device_names:
            self.logger.warning(
                "WMS component manager instantiated without any WMS device names provided. "
                "Weather station monitoring cannot be started."
            )
            return
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)

        self._stop_monitoring_flag.clear()

        self._wms_device_group.add(self._wms_device_names, timeout_ms=GROUP_REQUEST_TIMEOUT_MS)

        _wms_monitoring_started_future = self.executor.submit(self._start_monitoring)
        _wms_monitoring_started_future.add_done_callback(self._run_wms_group_polling)

    def _start_monitoring(self) -> None:
        """Start WMS Tango device monitoring of the weather station servers."""
        while not self._stop_monitoring_flag.wait(timeout=self._wms_polling_period):
            try:
                self.write_wms_group_attribute_value("adminMode", AdminMode.ONLINE)
                break
            except tango.DevFailed:
                self.logger.error(
                    "Failed to set WMS device(s) adminMode to ONLINE. One or more"
                    " WMS device(s) may be unavailable. Retrying"
                )

    def stop_communicating(self) -> None:
        """Stop WMS attr polling and clean up windspeed data buffers."""
        self._stop_monitoring_flag.set()

        self.executor.shutdown(wait=True, cancel_futures=True)
        self.executor = ThreadPoolExecutor(max_workers=1)

        self._wind_speed_buffer.clear()
        self._wind_gust_buffer.clear()

        try:
            self.write_wms_group_attribute_value("adminMode", AdminMode.OFFLINE)
            self._wms_device_group.remove_all()
        except tango.DevFailed:
            self.logger.error(
                "Failed to set WMS device(s) adminMode to OFFLINE. "
                "One or more WMS device(s) may be unavailable"
            )
        self._update_communication_state(CommunicationStatus.DISABLED)

    def _run_wms_group_polling(self, *args):
        """Periodically fetch WMS windspeeds and publish avg wind speed and gust."""
        while not self._stop_monitoring_flag.is_set():
            try:
                wind_speed_data_list = self.read_wms_group_attribute_value("windSpeed")
                # The returned data is a list of lists, where the index 0 is the
                # timestamp and index 1 is the polled windspeed
                # eg: [[timestamp, windspeed_wms_1], [timestamp, windspeed_wms_2],...]

                _current_time = wind_speed_data_list[0][0]

                mws = self._compute_mean_wind_speed(
                    wind_speed_data_list,
                    _current_time,
                )

                wg = self._process_wind_gust(
                    wind_speed_data_list,
                    _current_time,
                )

                self._update_component_state(
                    meanwindspeed=mws,
                    windgust=wg,
                )
            except Exception:
                self.logger.exception("Unexpected exception during WMS group polling")
            self._stop_monitoring_flag.wait(timeout=self._wms_polling_period)

    def _compute_mean_wind_speed(
        self,
        wind_speed_data: list[list[float, float]],
        current_time: float,
    ) -> float:
        """Calculate the mean wind speed from buffered wind speed data.

        This method extends the internal wind speed buffer with new wind speed data
        from the provided list of wind speeds fetched in the current polling cycle,
        prunes stale entries based on the current time and moving average period,
        and computes the mean wind speed from the remaining buffer data.

        :param wind_speed_data_list: A list of lists, where each inner list contains
            [timestamp, instantaneous wind speed] values.
        :type wind_speed_data_list: list[list[float, float]]
        :param current_time: The current timestamp used for pruning stale wind speed data.
        :type current_time: float

        :returns: The computed mean wind speed from the buffered data.
        :rtype: float
        """
        self._wind_speed_buffer.extend(wind_speed_data)

        self._prune_stale_windspeed_data(
            current_time,
            self._wind_speed_moving_average_period,
            self._wind_speed_buffer,
        )

        valid_wind_speeds = [ws[1] for ws in self._wind_speed_buffer if ws[1] is not None]
        try:
            _mean_wind_speed = sum(valid_wind_speeds) / len(valid_wind_speeds)
        except ZeroDivisionError:
            _mean_wind_speed = 0.0

        return _mean_wind_speed

    def _process_wind_gust(
        self,
        wind_speed_data_list: list[list[float, float]],
        current_time: float,
    ) -> float:
        """Determines the wind gust value from a buffer of maximum wind speed data points
        in the last 3 seconds or less.

        This method identifies the maximum instantaneous wind speed from the provided
        list of wind speeds fetched in the current polling cycle, appends it to the wind
        gust buffer, prunes stale data, and returns the max wind speed in the buffer as
        the current wind gust value.

        :param wind_speed_data_list: A list of lists, where each inner list contains
            [timestamp, instantaneous wind speed] values.
        :type wind_speed_data_list: list[list[float, float]]
        :param current_time: The current timestamp used for pruning stale wind speed data.
        :type current_time: float

        :returns: The maximum instantaneous wind speed (wind gust) in the buffer.
        :rtype: float
        """
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

        self._prune_stale_windspeed_data(
            current_time,
            self._wind_gust_period,
            self._wind_gust_buffer,
        )
        _wind_gust = max(ws[1] for ws in self._wind_gust_buffer)

        return _wind_gust

    def _prune_stale_windspeed_data(
        self,
        current_time: float,
        computation_window_period: float,
        wind_speed_buffer: deque,
    ) -> None:
        """Removes stale windspeed data points from the provided wind speed data buffer.

        This method prunes the `wind_speed_buffer` by removing data points whose timestamps
        are older than the expiry time, which is calculated as
        `current_time - computation_window_period`.

        :param current_time: The current timestamp
        :type current_time: float
        :param computation_window_period: The time window period over which the mean wind speed
            or the wind gust is being calculated
        :type computation_window_period: float
        :param wind_speed_buffer: The circular buffer containing windspeed data points
        :type wind_speed_buffer: collections.deque
        :return: None
        """
        _data_point_expiry_time = current_time - computation_window_period
        # wind_speed_buffer[0][0] represents the timestamp of the oldest buffer datapoint
        while wind_speed_buffer and (wind_speed_buffer[0][0] < _data_point_expiry_time):
            wind_speed_buffer.popleft()

    def read_wms_group_attribute_value(self, attribute_name: str) -> Any:
        """Reads the specified attribute from all devices in the WMS device group.

        Attempts to read the given attribute from each device in the group, collecting
        the value and timestamping it for each successful read. Communication state
        is updated based on the success or failure of the operation.

        :param attribute_name: The name of the attribute to read from each device
            in the group.
        :type attribute_name : str
        :return list of list: A list of lists, where each inner list contains the
            timestamp (float) and the attribute value read from a device.
        """
        reply_values = []
        read_error_raised = False
        try:
            grp_reply = self._wms_device_group.read_attribute(attribute_name)
            reply_timestamp = time.time()
            for reply in grp_reply:
                if reply.has_failed():
                    self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
                    err_msg = (
                        f"Failed to read attribute [{attribute_name}] "
                        f"on device [{reply.dev_name()}] of "
                        f"group [{self._wms_device_group.get_name()}]",
                    )
                    self.logger.error(err_msg)
                    read_error_raised = True
                else:
                    reply_values.append([reply_timestamp, reply.get_data().value])
                    # Only report comm state established if there were no read errors
                    if not read_error_raised:
                        self._update_communication_state(CommunicationStatus.ESTABLISHED)
        except tango.DevFailed as err:
            self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
            self.logger.error(
                "Exception raised on attempt to "
                f"read attribute [{attribute_name}] "
                f"of group [{self._wms_device_group.get_name()}]: {err}",
            )
        return reply_values

    def write_wms_group_attribute_value(self, attribute_name: str, attribute_value: Any) -> None:
        """Writes the specified attribute value to all devices in the WMS Tango device group.

        Attempts to write the given attribute value to the specified attribute across all devices
        in the WMS device group. Updates the communication state based on the success or failure
        of the write operation.

        :param attribute_name: The name of the attribute to write to each device in the group.
        :type attribute_name : str
        :param attribute_value: The value to write to the attribute.
        :type attribute_value : str
        :raises tango.DevFailed : If writing the attribute fails for any device in the group.
        """
        try:
            grp_reply = self._wms_device_group.write_attribute(attribute_name, attribute_value)
            for reply in grp_reply:
                if reply.has_failed():
                    raise tango.DevFailed
            self._update_communication_state(CommunicationStatus.ESTABLISHED)
        except tango.DevFailed as err:
            self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
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
