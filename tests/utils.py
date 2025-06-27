# pylint: disable=invalid-name,possibly-unused-variable,no-value-for-parameter
"""General utils for test devices"""
import queue
import random
import string
from typing import Any, Callable, List, Tuple

import numpy as np
import tango
from ska_control_model import CommunicationStatus

from ska_mid_dish_manager.utils.ska_epoch_to_tai import get_current_tai_timestamp_from_unix_time

MAX_ELEVATION = 85.0
MIN_ELEVATION = 14.8
MAX_AZIMUTH = 270.0
MIN_AZIMUTH = -270.0
AZ_SPEED_LIMIT_DEG_PER_S = 3.0
EL_SPEED_LIMIT_DEG_PER_S = 1.0


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


def calculate_slew_target(current_az, current_el, offset_az, offset_el):
    """
    Moves a point by specified offsets in azimuth and elevation,
    ensuring the result stays within defined constraints.

    :param current_az: Current azimuth value.
    :type value: float
    :param current_el: Current elevation value.
    :type value: float
    :param offset_az: Azimuth offset (positive or negative).
    :type value: float
    :param offset_el: Elevation offset (positive or negative).
    :type value: float
    :return: Tuple containing the constrained azimuth and elevation values.
    :rtype: Tuple[float, float]
    """
    # Calculate requested values
    requested_az = current_az + offset_az
    requested_el = current_el + offset_el

    # Constrained azimuth
    requested_az = min(MAX_AZIMUTH, max(MIN_AZIMUTH, requested_az))
    # Constrained elevation
    requested_el = min(MAX_ELEVATION, max(MIN_ELEVATION, requested_el))

    return requested_az, requested_el


# pylint: disable=too-many-locals
def generate_track_table(
    num_samples: int = 50,
    current_az: float = 0.0,
    current_el: float = 45.0,
    time_offset_seconds: float = 5,
    total_track_duration_seconds: float = 5,
) -> List[float]:
    """
    Generate a track table with smoothly varying azimuth and elevation values,
    starting from the current pointing.

    :param time_offset_seconds: The number of seconds from the current TAI time
                                at which the track generation should start.
    :param num_samples: The number of samples to generate in the track data.
    :param total_track_duration_seconds: The total duration of the track in seconds.
    :param current_az: The current azimuth to start from.
    :param current_el: The current elevation to start from.

    :returns: A list of floats representing [tai_timestamp, az_degrees, el_degrees]
              for all samples.
    """
    # --- Azimuth Logic ---
    start_az = np.clip(current_az, MIN_AZIMUTH, MAX_AZIMUTH)
    # Determine the preferred end azimuth based on which limit start_az is closer to.
    preferred_end_az = (
        MAX_AZIMUTH if abs(start_az - MIN_AZIMUTH) < abs(start_az - MAX_AZIMUTH) else MIN_AZIMUTH
    )
    # Calculate the actual change in azimuth, clipped by speed limits.
    az_change_actual = np.clip(
        preferred_end_az - start_az,
        -AZ_SPEED_LIMIT_DEG_PER_S * total_track_duration_seconds,
        AZ_SPEED_LIMIT_DEG_PER_S * total_track_duration_seconds,
    )
    end_az = start_az + az_change_actual
    az_values = np.linspace(start_az, end_az, num_samples)

    # --- Elevation Logic ---
    start_el = np.clip(current_el, MIN_ELEVATION, MAX_ELEVATION)
    # Determine the preferred end elevation.
    preferred_end_el = (
        MAX_ELEVATION
        if abs(start_el - MIN_ELEVATION) < abs(start_el - MAX_ELEVATION)
        else MIN_ELEVATION
    )
    # Calculate the actual change in elevation, clipped by speed limits.
    el_change_actual = np.clip(
        preferred_end_el - start_el,
        -EL_SPEED_LIMIT_DEG_PER_S * total_track_duration_seconds,
        EL_SPEED_LIMIT_DEG_PER_S * total_track_duration_seconds,
    )
    end_el = start_el + el_change_actual
    el_values = np.linspace(start_el, end_el, num_samples)

    # --- Generate TAI timestamps ---
    start_time_tai = get_current_tai_timestamp_from_unix_time() + time_offset_seconds
    time_step = total_track_duration_seconds / num_samples
    times_tai = start_time_tai + np.arange(num_samples) * time_step

    # --- Generate the final flat track table ---
    return [val for coordinate in zip(times_tai, az_values, el_values) for val in coordinate]
