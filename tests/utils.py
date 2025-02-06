# pylint: disable=invalid-name,possibly-unused-variable,no-value-for-parameter
"""General utils for test devices"""
import queue
import random
import string
from typing import Any, Callable, List, Tuple

import numpy as np
import tango
from ska_control_model import CommunicationStatus

class ComponentStateStore:
    """Store component state changes with useful functionality"""

    def __init__(self) -> None:
        self._queue = queue.Queue()

    def __call__(self, *args, **kwargs):
        """Store the update component_state

        :param event: latest_state
        :type event: dict
        """
        self._queue.put(kwargs)

    def get_queue_values(self, timeout: int = 3):
        """Get the values from the queue"""
        items = []
        try:
            while True:
                component_state = self._queue.get(timeout=timeout)
                items.append(component_state)
        except queue.Empty:
            return items

    def wait_for_value(  # pylint:disable=inconsistent-return-statements
        self, key: str, value: Any, timeout: int = 3
    ):
        """Wait for a value to arrive

        Wait `timeout` seconds for each fetch.

        :param key: The value key
        :type value: str
        :param value: The value to check for
        :type value: Any
        :param timeout: the get timeout, defaults to 3
        :type timeout: int, optional
        :raises RuntimeError: If None are found
        :return: True if found
        :rtype: bool
        """
        try:
            component_state = []
            while True:
                state = self._queue.get(timeout=timeout)
                if state.get(key) == value:
                    return True
                component_state.append(state)
        except queue.Empty as err:
            raise RuntimeError(
                (
                    f"Never got a state with key [{key}], value "
                    f"[{value}], got [{component_state}]"
                )
            ) from err

    def clear_queue(self):
        """Clear out the queue"""
        while not self._queue.empty():
            self._queue.get()


class EventStore:
    """Store events with useful functionality"""

    def __init__(self) -> None:
        """Init Store"""
        self._queue = queue.Queue()

    def push_event(self, event: tango.EventData):
        """Store the event

        :param event: Tango event
        :type event: tango.EventData
        """
        self._queue.put(event)

    def wait_for_value(  # pylint:disable=inconsistent-return-statements
        self,
        value: Any,
        timeout: int = 3,
        proxy: Any = None,
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
                if event.attr_value is None:
                    continue
                if isinstance(event.attr_value.value, np.ndarray):
                    if (event.attr_value.value == value).all():
                        return True
                    if np.isclose(event.attr_value.value, value).all():
                        return True
                    continue
                if event.attr_value.value != value:
                    continue
                if event.attr_value.value == value:
                    return True
        except queue.Empty as err:
            ev_vals = self.extract_event_values(events)
            if proxy:
                component_states = proxy.GetComponentStates()
                raise RuntimeError(
                    f"Never got an event with value [{value}] got [{ev_vals}]"
                    f"with component states: [{component_states}]"
                ) from err
            raise RuntimeError(f"Never got an event with value [{value}] got [{ev_vals}]") from err

    def wait_for_condition(self, condition: Callable, timeout: int = 3) -> bool:
        """Wait for a generic condition.

        Wait `timeout` seconds for each fetch.

        :param condition: Function that represents condition to check
        :type value: Callable
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
                if condition(event.attr_value.value):
                    return True
        except queue.Empty as err:
            ev_vals = self.extract_event_values(events)
            raise RuntimeError(f"Never got an event that meets condition got [{ev_vals}]") from err

    def wait_for_quality(  # pylint:disable=inconsistent-return-statements
        self, value: tango.AttrQuality, timeout: int = 3
    ):
        """Wait for a quality value to arrive

        Wait `timeout` seconds for each fetch.

        :param value: The value to check for
        :type value: tango.AttrQuality
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
                if event.attr_value is None:
                    continue
                if event.attr_value.quality == value:
                    return event
        except queue.Empty as err:
            event_str = "\n".join([str(i) for i in events])
            raise RuntimeError(
                f"Never got an event with quality [{value}] got [{event_str}]"
            ) from err

    # pylint:disable=inconsistent-return-statements
    def wait_for_command_result(self, command_id: str, command_result: Any, timeout: int = 3):
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

    def wait_for_command_id(self, command_id: str, timeout: int = 3):
        """Wait for a long running command to complete

        Wait `timeout` seconds for each fetch.

        :param command_id: The long running command ID
        :type command_id: str
        :param timeout: the get timeout, defaults to 3
        :type timeout: int, optional
        :raises RuntimeError: If none are found
        :return: The result of the long running command
        :rtype: str
        """
        events = []
        try:
            while True:
                event = self._queue.get(timeout=timeout)
                events.append(event)
                if not event.attr_value:
                    continue
                if not isinstance(event.attr_value.value, tuple):
                    continue
                if len(event.attr_value.value) != 2:
                    continue
                (lrc_id, _) = event.attr_value.value
                if command_id == lrc_id and event.attr_value.name == "longrunningcommandresult":
                    return events
        except queue.Empty as err:
            event_info = [(event.attr_value.name, event.attr_value.value) for event in events]
            raise RuntimeError(
                f"Never got an LRC result from command [{command_id}],",
                f" but got [{event_info}]",
            ) from err

    def wait_for_progress_update(self, progress_message: str, timeout: int = 3):
        """Wait for a long running command progress update

        Wait `timeout` seconds for each fetch.

        :param progress_message: The progress message to wait for
        :type progress_message: str
        :param timeout: the get timeout, defaults to 3
        :type timeout: int, optional
        :raises RuntimeError: If none are found
        :return: The result of the long running command
        :rtype: str
        """
        events = []
        try:
            while True:
                event = self._queue.get(timeout=timeout)
                events.append(event)
                if not event.attr_value:
                    continue
                if not isinstance(event.attr_value.value, tuple):
                    continue
                progress_update = str(event.attr_value.value)
                if (
                    progress_message in progress_update
                    and event.attr_value.name == "longrunningcommandprogress"
                ):
                    return events
        except queue.Empty as err:
            event_info = [(event.attr_value.name, event.attr_value.value) for event in events]
            raise RuntimeError(
                f"Never got a progress update with [{progress_message}],",
                f" but got [{event_info}]",
            ) from err

    @classmethod
    def filter_id_events(
        cls, events: List[tango.EventData], unique_id: str
    ) -> List[tango.EventData]:
        """Filter out only events from unique_id

        :param events: Events
        :type events: List[tango.EventData]
        :param unique_id: command ID
        :type unique_id: str
        :return: Filtered list of events
        :rtype: List[tango.EventData]
        """
        return [event for event in events if unique_id in str(event.attr_value.value)]

    def wait_for_n_events(self, event_count: int, timeout: int = 3):
        """Wait for N number of events

        Wait `timeout` seconds for each fetch.

        :param event_count: The number of events to wait for
        :type command_id: int
        :param timeout: the get timeout, defaults to 3
        :type timeout: int, optional
        :raises RuntimeError: If none are found
        :return: The result of the long running command
        :rtype: str
        """
        events = []
        try:
            while len(events) != event_count:
                event = self._queue.get(timeout=timeout)
                events.append(event)
            return events
        except queue.Empty as err:
            raise RuntimeError(
                f"Did not get {event_count} events, ",
                f"got {len(events)} events",
            ) from err

    def clear_queue(self):
        """Clear out the queue"""
        while not self._queue.empty():
            self._queue.get()

    #  pylint: disable=unused-argument
    def get_queue_events(self, timeout: int = 3):
        """Get all the events out of the queue"""
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


def set_ignored_devices(device_proxy, ignore_spf, ignore_spfrx):
    """Sets ignored devices on DishManager."""

    if device_proxy.ignoreSpf != ignore_spf:
        spf_connection_event_store = EventStore()
        device_proxy.subscribe_event(
            "spfConnectionState",
            tango.EventType.CHANGE_EVENT,
            spf_connection_event_store,
        )

        device_proxy.ignoreSpf = ignore_spf

        if ignore_spf:
            spf_connection_event_store.wait_for_value(CommunicationStatus.DISABLED)
        else:
            spf_connection_event_store.wait_for_value(CommunicationStatus.ESTABLISHED)

    if device_proxy.ignoreSpfrx != ignore_spfrx:
        spfrx_connection_event_store = EventStore()

        device_proxy.subscribe_event(
            "spfrxConnectionState",
            tango.EventType.CHANGE_EVENT,
            spfrx_connection_event_store,
        )

        device_proxy.ignoreSpfrx = ignore_spfrx

        if ignore_spfrx:
            spfrx_connection_event_store.wait_for_value(CommunicationStatus.DISABLED)
        else:
            spfrx_connection_event_store.wait_for_value(CommunicationStatus.ESTABLISHED)


def generate_random_text(length=10):
    """Generate a random string."""
    letters = string.ascii_letters
    return "".join(random.choice(letters) for _ in range(length))
