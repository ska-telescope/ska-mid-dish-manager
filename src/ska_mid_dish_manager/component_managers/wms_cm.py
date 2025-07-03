"""Specialization for WMS functionality."""

from concurrent.futures import ThreadPoolExecutor
import logging
import math
import threading
from collections import deque
from typing import Any, Callable, Optional

import tango
import time
from ska_control_model import AdminMode, CommunicationStatus
from ska_tango_base.base import BaseComponentManager
from threading import Thread

GROUP_REQUEST_TIMEOUT_MS = 3000

class WMSComponentManager(BaseComponentManager):
    """Specialization for WMS functionality"""
    def __init__(
        self,
        logger: logging.Logger,
        wms_instances,
        *args: Any,
        component_state_callback: Optional[Callable] = None,
        state_update_lock: Optional[threading.Lock] = None,
        wms_polling_period: Optional[float] = 60,
        wind_speed_moving_average_period: Optional[float] = 600,
        **kwargs: Any,
    ):
        self.logger = logger
        self._wms_instances = wms_instances
        self._wms_instance_count = len(wms_instances)
        self._wms_polling_period = wms_polling_period
        self._wind_speed_moving_average_period = wind_speed_moving_average_period

        self._wms_device_group = tango.Group("wms_devices")

        # Determine the max buffer length. Once the buffer is full we will have enough data
        # points to determine the rolling average (mean wind speed)
        self._buffer_length = self._wms_instance_count * (
            self._wind_speed_moving_average_period / self._wms_polling_period
        )
        self._buffer_length = int(math.ceil(self._buffer_length) + self._wms_instance_count)

        # Circular buffer storing all wind speed data points as they are polled
        self._ws_buffer_deque = deque(maxlen=self._buffer_length)

        self._wms_attr_polling_timer = threading.Timer(
            self._wms_polling_period, self._poll_wms_wind_speed_data
        )

        self._stop_monitoring_flag = threading.Event()

        monitored_attr_names = ("meanwindspeed",)
        super().__init__(
            logger,
            monitored_attr_names,
            *args,
            component_state_callback=component_state_callback,
            **kwargs,
        )
        if state_update_lock is not None:
            self._component_state_lock = state_update_lock

    def start_communicating(self) -> None:
        """Add WMS device to group and initiate WMS attr polling."""
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)

        if self._stop_monitoring_flag.is_set():
            self._stop_monitoring_flag.clear()

        for new_wms_instance in self._wms_instances:
            wms_device_name = "mid/wms/" + str(new_wms_instance)
            self._wms_device_group.add(wms_device_name, timeout_ms=GROUP_REQUEST_TIMEOUT_MS)

        # Create a thread to recursively attempt a write to the adminMode attribute and once
        # the write succeeds, the callback should kick off the wms data polling
        executor = ThreadPoolExecutor(max_workers=1)
        _wms_activated_future = executor.submit(self._activate_wms_devices)
        _wms_activated_future.add_done_callback(self._wms_communication_established)

        # try:
        #     self.write_wms_group_attribute_value("adminMode", AdminMode.ONLINE)
        #     self._update_communication_state(CommunicationStatus.ESTABLISHED)
        #     self._poll_wms_wind_speed_data()
        # except:
        #     self.logger.error(
        #         "Failed to set WMS device(s) adminMode to ONLINE. One or more WMS device may be unavailable"
        #     )

    def _activate_wms_devices(self) -> None:
        # Function will recusively, within a separate thread, try to write the admin Mode to ONLINE
        while not self._stop_monitoring_flag.is_set():
            try:
                self.write_wms_group_attribute_value("adminMode", AdminMode.ONLINE)
                break
            except:
                self.logger.error(
                    "Failed to set WMS device(s) adminMode to ONLINE. One or more"
                    " WMS device(s) may be unavailable. Retrying"
                )
                time.sleep(1)

    def _wms_communication_established(self) -> None:
        self._update_communication_state(CommunicationStatus.ESTABLISHED)
        self._poll_wms_wind_speed_data()


    def stop_communicating(self) -> None:
        """Stop WMS attr polling."""
        if self._wms_attr_polling_timer.is_alive():
            self._wms_attr_polling_timer.cancel()

        if not self._stop_monitoring_flag.is_set():
            self._stop_monitoring_flag.set()

        try:
            self.write_wms_group_attribute_value("adminMode", AdminMode.OFFLINE)
            self._wms_device_group.remove_all()
            self._update_communication_state(CommunicationStatus.DISABLED)
        except:
            self.logger.error(
                "Failed to set WMS device(s) adminMode to OFFLINE. One or more WMS device may be unavailable"
            )

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
        """Fetch WMS windspeed data and publish it to the rolling avg calc"""
        self.logger.info("RRR Requesting wms tango group windspeed polling")
        wind_speed_list = self.read_wms_group_attribute_value("wind_speed")
        self._compute_mean_wind_speed(wind_speed_list)
        self._restart_polling_timer()


    def _compute_mean_wind_speed(self, wind_speed_data) -> None:
        """Calculate the mean wind speed and update the component state."""
        # Push the received wind speed data points to the list
        self._ws_buffer_deque.extendleft(wind_speed_data)

        # Ensure sufficient number of wind speed data points covering the complete
        # window period time span before computing mean wind speed
        if len(self._ws_buffer_deque) == self._buffer_length:
            _mean_wind_speed = sum(self._ws_buffer_deque) / self._buffer_length
            self.logger.info(f"Computed mean wind speed: {_mean_wind_speed}")
            self._update_component_state(meanwindspeed=_mean_wind_speed)

    def read_wms_group_attribute_value(self, attribute_name: str) -> Any:
        """Return list of group attributes"""
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
        except:
            self.logger.error(
                "Exception raised on attempt to read attribute [%s] of group [%s].",
                attribute_name,
                self._wms_device_group.get_name(),
            )

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
        except:
            self.logger.error(
                "Exception raised on attempt to write attribute [%s] of group [%s].",
                attribute_name,
                self._wms_device_group.get_name(),
            )
            raise
