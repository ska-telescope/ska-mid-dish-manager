import queue
import time
from threading import Event
from typing import Any, List, Optional, Tuple

import numpy as np
import tango
from tango import CmdArgType


def poll_for_attribute_value(
    device_proxy: tango.DeviceProxy, attribute: Any, value: Any, timeout: int = 5
) -> Optional[bool]:
    """Wait for a devices attribute value to match the given value."""
    t_end = time.time() + timeout

    actual_value = None
    while time.time() < t_end:
        actual_value = device_proxy.read_attribute(attribute).value

        if isinstance(actual_value, np.ndarray):
            all_values_equal = np.isclose(actual_value, value).all()

            if all_values_equal:
                return True
        else:
            if actual_value == value:
                return True

    raise RuntimeError(f"Never got expected value [{value}] got [{actual_value}]")


def retrieve_attr_value(dev_proxy, attr_name):
    """Get the attribute reading from device"""
    current_val = dev_proxy.read_attribute(attr_name)
    if current_val.type == CmdArgType.DevEnum:
        current_val = getattr(dev_proxy, attr_name).name
    elif current_val.type == CmdArgType.DevState:
        current_val = str(current_val.value)
    else:
        current_val = current_val.value
    return current_val


def tango_dev_proxy(device_name, logger):
    """Provision a device proxy to a tango device server"""
    retry_time = 0.5  # seconds
    retry = 0
    max_retries = 3
    retry_event = Event()

    while retry <= max_retries and not retry_event.is_set():
        try:
            dp = tango.DeviceProxy(device_name)
        except tango.DevFailed as ex:
            reasons = {dev_error.reason for dev_error in ex.args}
            if "API_CantConnectToDatabase" in reasons:
                retry += 1
                logger.debug(
                    f"Failed to connect to database after {retry + 1} tries. "
                    f"Retrying {device_name} device server connection"
                )
                retry_event.wait(retry_time)
            else:
                logger.error(f" {device_name} device server connection failed. Reasons: {reasons}")
                raise
        else:
            logger.debug(f"{device_name} device server connection established")
            return dp
    raise Exception(f"Connection to the {device_name} device server failed")


class EventStore:
    """Store events with useful functionality"""

    def __init__(self) -> None:
        self._queue = queue.Queue()

    def push_event(self, event: tango.EventData):
        """Store the event

        :param event: Tango event
        :type event: tango.EventData
        """
        self._queue.put(event)

    def wait_for_value(  # pylint:disable=inconsistent-return-statements
        self, value: Any, timeout: int = 3
    ):
        """Wait for a value to arrive

        Wait `timeout` seconds for each fetch.

        :param value: The value to check for
        :type value: Any
        :param timeout: the get timeout, defaults to 3
        :type timeout: int, optional
        :raises RuntimeError: If None are found
        :return: True if found
        :rtype: bool
        """

        try:
            events = []
            while True:
                event = self._queue.get(timeout=timeout)
                events.append(event)
                if not event.attr_value:
                    continue
                if isinstance(event.attr_value.value, np.ndarray):
                    if (event.attr_value.value != value).all():
                        continue
                    if (event.attr_value.value == value).all():
                        return True

                if event.attr_value.value != value:
                    continue
                if event.attr_value.value == value:
                    return True
        except queue.Empty as err:
            ev_vals = self.extract_event_values(events)
            raise RuntimeError(f"Never got an event with value [{value}] got [{ev_vals}]") from err

    # pylint:disable=inconsistent-return-statements
    def wait_for_command_result(self, command_id: str, command_result: Any, timeout: int = 5):
        """Wait for a long running command result

        Wait `timeout` seconds for each fetch.

        :param command_id: The long running command ID
        :type command_id: str
        :param timeout: the get timeout, defaults to 3
        :type timeout: int, optional
        :raises RuntimeError: If none are found
        :return: The result of the long running command
        :rtype: str
        """
        try:
            while True:
                event = self._queue.get(timeout=timeout)
                if not event.attr_value:
                    continue
                if not isinstance(event.attr_value.value, tuple):
                    continue
                if len(event.attr_value.value) != 2:
                    continue
                (lrc_id, lrc_result) = event.attr_value.value
                if command_id == lrc_id and command_result == lrc_result:
                    return True
        except queue.Empty as err:
            raise RuntimeError(f"Never got an LRC result from command [{command_id}]") from err

    def clear_queue(self):
        while not self._queue.empty():
            self._queue.get()

    #  pylint: disable=unused-argument
    def get_queue_events(self, timeout: int = 3):
        items = []
        try:
            while True:
                items.append(self._queue.get(timeout=timeout))
        except queue.Empty:
            return items

    @classmethod
    def extract_event_values(cls, events: List[tango.EventData]) -> List[Tuple]:
        """Get the values out of events

        :param events: List of events
        :type events: List[tango.EventData]
        :return: List of value tuples
        :rtype: List[Tuple]
        """
        event_info = [
            (event.attr_value.name, event.attr_value.value, event.device) for event in events
        ]
        return event_info

    def get_queue_values(self, timeout: int = 3):
        """Get the values from the queue"""
        items = []
        try:
            while True:
                event = self._queue.get(timeout=timeout)
                items.append((event.attr_value.name, event.attr_value.value))
        except queue.Empty:
            return items

    @classmethod
    def get_data_from_events(cls, events: List[tango.EventData]) -> List[Tuple]:
        """Retrieve the event info from the events

        :param events: list of
        :type events: List[tango.EventData]
        """
        return [(event.attr_value.name, event.attr_value.value) for event in events]
