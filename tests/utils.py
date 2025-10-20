"""General utils for test devices."""

import math
import queue
import random
import string
import time
from typing import Any, Callable, Dict, List, Tuple

import numpy as np
import tango
from matplotlib import pyplot as plt
from ska_control_model import CommunicationStatus

from ska_mid_dish_manager.models.dish_enums import PointingState, TrackTableLoadMode
from ska_mid_dish_manager.utils.ska_epoch_to_tai import get_current_tai_timestamp_from_unix_time

MAX_ELEVATION = 85.0
MIN_ELEVATION = 14.8
MAX_AZIMUTH = 270.0
MIN_AZIMUTH = -270.0
AZ_SPEED_LIMIT_DEG_PER_S = 3.0
EL_SPEED_LIMIT_DEG_PER_S = 1.0


class ComponentStateStore:
    """Store component state changes with useful functionality."""

    def __init__(self) -> None:
        self._queue = queue.Queue()

    def __call__(self, *args, **kwargs):
        """Store the update component_state.

        :param event: latest_state
        :type event: dict
        """
        self._queue.put(kwargs)

    def get_queue_values(self, timeout: int = 3):
        """Get the values from the queue."""
        items = []
        try:
            while True:
                component_state = self._queue.get(timeout=timeout)
                items.append(component_state)
        except queue.Empty:
            return items

    def get_queue_values_timeout(self, timeout: int = 3) -> List[Tuple[Any, Any]]:
        """Get the values from the queue with an overall timeout."""
        items = []
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                event = self._queue.get(timeout=timeout)
                items.append((event.attr_value.name, event.attr_value.value))
        except queue.Empty:
            pass
        return items

    def wait_for_value(  # pylint:disable=inconsistent-return-statements
        self, key: str, value: Any, timeout: int = 3
    ):
        """Wait for a value to arrive.

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
                (f"Never got a state with key [{key}], value [{value}], got [{component_state}]")
            ) from err

    def clear_queue(self):
        """Clear out the queue."""
        while not self._queue.empty():
            self._queue.get()


class EventStore:
    """Store events with useful functionality."""

    def __init__(self) -> None:
        """Init Store."""
        self._queue = queue.Queue()

    def push_event(self, event: tango.EventData):
        """Store the event.

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
        """Wait for a value to arrive.

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
        """Wait for a quality value to arrive.

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
        """Wait for a long running command result.

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
        """Wait for a long running command to complete.

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
        """Wait for a long running command progress update.

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
        """Filter out only events from unique_id.

        :param events: Events
        :type events: List[tango.EventData]
        :param unique_id: command ID
        :type unique_id: str
        :return: Filtered list of events
        :rtype: List[tango.EventData]
        """
        return [event for event in events if unique_id in str(event.attr_value.value)]

    def wait_for_n_events(self, event_count: int, timeout: int = 3):
        """Wait for N number of events.

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
        """Clear out the queue."""
        while not self._queue.empty():
            self._queue.get()

    #  pylint: disable=unused-argument
    def get_queue_events(self, timeout: int = 3):
        """Get all the events out of the queue."""
        items = []
        try:
            while True:
                items.append(self._queue.get(timeout=timeout))
        except queue.Empty:
            return items

    @classmethod
    def extract_event_values(cls, events: List[tango.EventData]) -> List[Tuple]:
        """Get the values out of events.

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
        """Get the values from the queue."""
        items = []
        try:
            while True:
                event = self._queue.get(timeout=timeout)
                items.append((event.attr_value.name, event.attr_value.value))
        except queue.Empty:
            return items

    @classmethod
    def get_data_from_events(cls, events: List[tango.EventData]) -> List[Tuple]:
        """Retrieve the event info from the events.

        :param events: list of
        :type events: List[tango.EventData]
        """
        return [(event.attr_value.name, event.attr_value.value) for event in events]


def set_ignored_devices(device_proxy, ignore_spf, ignore_spfrx):
    """Sets ignored devices on DishManager."""
    if device_proxy.ignoreSpf != ignore_spf:
        spf_connection_event_store = EventStore()
        spf_sub_id = device_proxy.subscribe_event(
            "spfConnectionState",
            tango.EventType.CHANGE_EVENT,
            spf_connection_event_store,
        )

        device_proxy.ignoreSpf = ignore_spf

        if ignore_spf:
            spf_connection_event_store.wait_for_value(CommunicationStatus.DISABLED)
        else:
            spf_connection_event_store.wait_for_value(CommunicationStatus.ESTABLISHED)
        device_proxy.unsubscribe_event(spf_sub_id)

    if device_proxy.ignoreSpfrx != ignore_spfrx:
        spfrx_connection_event_store = EventStore()

        spfrx_sub_id = device_proxy.subscribe_event(
            "spfrxConnectionState",
            tango.EventType.CHANGE_EVENT,
            spfrx_connection_event_store,
        )

        device_proxy.ignoreSpfrx = ignore_spfrx

        if ignore_spfrx:
            spfrx_connection_event_store.wait_for_value(CommunicationStatus.DISABLED)
        else:
            spfrx_connection_event_store.wait_for_value(CommunicationStatus.ESTABLISHED)
        device_proxy.unsubscribe_event(spfrx_sub_id)


def generate_random_text(length=10):
    """Generate a random string."""
    letters = string.ascii_letters
    return "".join(random.choice(letters) for _ in range(length))


def calculate_slew_target(current_az, current_el, offset_az, offset_el):
    """Moves a point by specified offsets in azimuth and elevation,
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


def generate_track_table(
    num_samples: int = 50,
    current_az: float = 0.0,
    current_el: float = 45.0,
    time_offset_seconds: float = 5,
    total_track_duration_seconds: float = 5,
    controller_current_time_tai: float | None = None,
) -> List[float]:
    """Generate a track table with smoothly varying azimuth and elevation values,
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
    current_time = controller_current_time_tai or get_current_tai_timestamp_from_unix_time()
    start_time_tai = current_time + time_offset_seconds
    time_step = total_track_duration_seconds / num_samples
    times_tai = start_time_tai + np.arange(num_samples) * time_step

    # --- Generate the final flat track table ---
    return [val for coordinate in zip(times_tai, az_values, el_values) for val in coordinate]


def handle_tracking_table(
    ds_manager_proxy: tango.DeviceProxy,
    dish_manager_proxy: tango.DeviceProxy,
    table: list[tuple[float, float, float]],
    start_time_tai: float,
    pointing_tolerance_arcsec: float,
    table_load_chunk_size: int,
    table_load_lead_time: int,
    event_store_class: Any,
) -> None:
    """Handle tracking the points from the given table.

    :param ds_manager_proxy: Tango device proxy to the DSManager device
    :type dish_manager_proxy: tango.DeviceProxy
    :param dish_manager_proxy: Tango device proxy to the DishManager device
    :type dish_manager_proxy: tango.DeviceProxy
    :param table: List of (time_offset, azimuth, elevation) tuples to track.
    :type table: list[tuple[float, float, float]]
    :param start_time_tai: Absolute TAI time (in seconds) at which to start tracking.
    :type start_time_tai: float
    :param pointing_tolerance_arcsec: Tolerance (in arcsec) for pointing comparison
    :type pointing_tolerance_arcsec: float
    :param table_load_chunk_size: Number of points to send in each chunk.
    :type table_load_chunk_size: int
    :param table_load_lead_time: Lead time (in seconds) to send each chunk.
    :type table_load_lead_time: int
    :param event_store_class: Class used to store or observe events.
    :type event_store_class: type
    """
    sub_ids = []
    pointing_state_event_store = event_store_class()
    sub_ids.append(
        dish_manager_proxy.subscribe_event(
            "pointingstate",
            tango.EventType.CHANGE_EVENT,
            pointing_state_event_store,
        )
    )
    end_index_event_store = event_store_class()
    sub_ids.append(
        dish_manager_proxy.subscribe_event(
            "trackTableEndIndex",
            tango.EventType.CHANGE_EVENT,
            end_index_event_store,
        )
    )
    achieved_pointing_event_store = event_store_class()
    sub_ids.append(
        dish_manager_proxy.subscribe_event(
            "achievedPointing",
            tango.EventType.CHANGE_EVENT,
            achieved_pointing_event_store,
        )
    )
    achieved_target_lock_event_store = event_store_class()
    sub_ids.append(
        dish_manager_proxy.subscribe_event(
            "achievedTargetLock",
            tango.EventType.CHANGE_EVENT,
            achieved_target_lock_event_store,
        )
    )
    # Ensure the first table load is done with TrackTableLoadMode.NEW
    dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.NEW

    # Loop to load points from the csv file
    first_load = True
    chunk_index = 0
    time_of_last_point_in_chunk = 0

    try:
        while True:
            if not first_load:
                time.sleep(0.5)

                if dish_manager_proxy.pointingState not in [
                    PointingState.TRACK,
                    PointingState.SLEW,
                ]:
                    print(
                        "Something went wrong during track, PointingState should be TRACK or SLEW"
                        f" but got {dish_manager_proxy.pointingState.name}."
                        f" AchievedPointing = {dish_manager_proxy.achievedpointing}."
                        f" trackTableCurrentIndex = {dish_manager_proxy.trackTableCurrentIndex}"
                    )
                    return
                # If there are still points loaded with enough lead time, then continue waiting
                if (
                    time_of_last_point_in_chunk - ds_manager_proxy.GetCurrentTAIOffset()
                    > table_load_lead_time
                ):
                    continue

            # Get the next chunk
            chunk = table[chunk_index : chunk_index + table_load_chunk_size]
            if not chunk:
                # No more data to load, break and wait for the track to complete
                break
            chunk_index += table_load_chunk_size

            # Generate the track table (adding the start time to each of the offsets)
            chunk_track_table: list[Any] = []
            for offset_tai, az, el in chunk:
                chunk_track_table += [start_time_tai + offset_tai, az, el]
            time_of_last_point_in_chunk = chunk_track_table[-3]

            # Load the track table chunk
            end_index_event_store.clear_queue()
            dish_manager_proxy.programTrackTable = chunk_track_table

            if first_load:
                # Configure target lock with ThresholdTimePeriod of 0.1s
                dish_manager_proxy.configureTargetLock = [pointing_tolerance_arcsec, 0.1]
                # Start tracking and then set the track table load mode to APPEND
                dish_manager_proxy.Track()
                pointing_state_event_store.wait_for_value(PointingState.TRACK, timeout=30)
                achieved_target_lock_event_store.wait_for_value(True, timeout=30)
                dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.APPEND
                first_load = False
            else:
                # TODO: PLC end index updates unexpectedly (1000 -> 1952, where 2000 was expected)
                # expected_next_end_index = ((end_index + len(chunk) - 1) % 10000) + 1
                # end_index_event_store.wait_for_value(expected_next_end_index, timeout=5)

                # Solution until above comment is resolved
                end_index_event_store.wait_for_n_events(1, timeout=5)

        # Wait for the track to finish
        final_tai_value = start_time_tai + table[-1][0]
        wait_duration = final_tai_value - ds_manager_proxy.GetCurrentTAIOffset()
        wait_duration *= 1.10  # 10% leeway
        pointing_state_event_store.wait_for_value(PointingState.READY, timeout=wait_duration)
    finally:
        dish_manager_proxy.TrackStop()
        if dish_manager_proxy.pointingState != PointingState.READY:
            pointing_state_event_store.wait_for_value(PointingState.READY, timeout=60)
        for sub_id in sub_ids:
            dish_manager_proxy.unsubscribe_event(sub_id)


def save_tracking_test_plots(
    desired_trajectory: list[tuple[float, float, float]],
    achieved_trajectory: list[tuple[float, float, float]],
    err_tai_list: list[float],
    err_angular_list: list[float],
    save_file_path: str,
) -> None:
    """Save plots comparing desired and achieved pointing trajectories.

    :param desired_trajectory: List of (tai, azimuth, elevation) tuples for desired points.
    :param achieved_trajectory: List of (tai, azimuth, elevation) tuples observed during tracking.
    :param err_tai_list: List of TAI timestamps for which errors were computed.
    :param err_angular_list: Angular error values (arcsec) corresponding to err_tai_list.
    :param save_file_path: Output file path for saving the plot.
    """
    _, ax = plt.subplots(3, 1, figsize=(18, 10), sharex=True)

    # Desired
    desired_tai_list = [tai for tai, _, _ in desired_trajectory]
    desired_az_list = [az for _, az, _ in desired_trajectory]
    desired_el_list = [el for _, _, el in desired_trajectory]

    # Achieved
    achieved_tai_list = [tai for tai, _, _ in achieved_trajectory]
    achieved_az_list = [az for _, az, _ in achieved_trajectory]
    achieved_el_list = [el for _, _, el in achieved_trajectory]

    # Azimuth plot
    ax[0].plot(desired_tai_list, desired_az_list, label="Desired Az", color="blue")
    ax[0].plot(
        achieved_tai_list, achieved_az_list, label="Achieved Az", color="orange", linestyle="--"
    )
    ax[0].set_ylabel("Azimuth (deg)")
    ax[0].legend()
    ax[0].grid(True)

    # Elevation plot
    ax[1].plot(desired_tai_list, desired_el_list, label="Desired El", color="blue")
    ax[1].plot(
        achieved_tai_list, achieved_el_list, label="Achieved El", color="orange", linestyle="--"
    )
    ax[1].set_ylabel("Elevation (deg)")
    ax[1].legend()
    ax[1].grid(True)

    # Error plot
    ax[2].plot(err_tai_list, err_angular_list, label="Angular Error", color="red")
    ax[2].set_ylabel("Error (arcsec)")
    ax[2].legend()
    ax[2].grid(True)
    ax[2].set_xlabel("TAI")

    plt.tight_layout()
    plt.savefig(save_file_path)


def spherical_to_vector(az_value_rad: float, el_value_rad: float) -> tuple[float, float, float]:
    """Calculates 3D vector defined by azimuth and elevation."""
    x_value = math.cos(el_value_rad) * math.cos(az_value_rad)
    y_value = math.cos(el_value_rad) * math.sin(az_value_rad)
    z_value = math.sin(el_value_rad)
    return x_value, y_value, z_value


def radians_to_arcsec(radians: float) -> float:
    """Convert an angle from radians to arcseconds.

    :param radians: Angle in radians
    :return: Angle in arcseconds
    """
    return radians * (180 / math.pi) * 3600


def calculate_on_source_dev(
    p_desired: tuple[float, float, float], p_actual: tuple[float, float, float]
) -> float:
    """Calculates the angular error between the desired and actual vectors."""
    x_desired, y_desired, z_desired = p_desired
    x_actual, y_actual, z_actual = p_actual
    dot_product = (x_desired * x_actual) + (y_desired * y_actual) + (z_desired * z_actual)
    if abs(dot_product) > 1:
        dot_product = round(dot_product, 6)
    try:
        err = math.acos(dot_product)
    except ValueError:
        print("Check vectors are normalized. arccos argument is > 1 or < -1.")
        raise
    return radians_to_arcsec(err)


def get_angular_error_between_points(az_1: float, el_1: float, az_2: float, el_2: float) -> float:
    """Calculates the angular error between two positions."""
    vector_1_point = spherical_to_vector(math.radians(az_1), math.radians(el_1))
    vector_2_point = spherical_to_vector(math.radians(az_2), math.radians(el_2))
    return calculate_on_source_dev(p_desired=vector_1_point, p_actual=vector_2_point)


def compare_trajectories(
    desired_trajectory: list[tuple[float, float, float]],
    achieved_trajectory: list[tuple[float, float, float]],
    pointing_tolerance_arcsec: float,
) -> tuple[list[str], list[float], list[float]]:
    """Compares desired and achieved pointing trajectories by computing interpolated errors.

    :param desired_trajectory: List of (tai, azimuth, elevation) tuples representing the desired
        path.
    :type desired_trajectory: list[tuple[float, float, float]]
    :param achieved_trajectory: List of (tai, azimuth, elevation) tuples representing the actual
        path.
    :type achieved_trajectory: list[tuple[float, float, float]]
    :param pointing_tolerance_arcsec: Tolerance (in arcsec) for pointing comparison
    :type pointing_tolerance_arcsec: float

    :return: A tuple of:
    - List of mismatch strings (if any).
    - List of TAI timestamps where error was computed.
    - List of angular errors (deg).
    :rtype: tuple[list[str], list[float], list[float]]
    """
    achieved_idx = 0
    mismatches = []
    err_tai_list = []
    err_angular_list = []
    achieved_len = len(achieved_trajectory)
    _, start_point_az, start_point_el = desired_trajectory[0]

    # Loop to check that point in the desired trajectory was met
    for desired_tai, desired_az, desired_el in desired_trajectory:
        # If its the start point then no event would be received and we can move on.
        # Check if the desired tai is before the first received event and if it is the start pos
        is_tai_early = desired_tai < achieved_trajectory[0][0]
        is_start_pos = desired_az == start_point_az and desired_el == start_point_el
        if is_tai_early and is_start_pos:
            continue

        # AchievedPointing events may not be received at exactly the same time as the desired
        # offsets. The below code finds the closest achieved points to the desired time and
        # interpolates their az/el values to the desired time to get a more accurate measure of
        # the error at that time.
        while (
            achieved_idx + 1 < achieved_len
            and achieved_trajectory[achieved_idx + 1][0] < desired_tai
        ):
            achieved_idx += 1

        if achieved_idx + 1 >= achieved_len:
            # desired point is after the last achieved event which means the trajectory might be
            # flat. If so, then the last received az/el event should still be within tolerance of
            # the desired value.
            last_az, last_el = achieved_trajectory[-1][1:3]
            angular_err = get_angular_error_between_points(
                desired_az, desired_el, last_az, last_el
            )
            is_idle = angular_err < pointing_tolerance_arcsec

            if is_idle:
                # Dish is likely idle and no more events are generated — skip this point
                continue

            mismatches.append(f"No future point for interpolation at TAI={desired_tai:.6f}")
            continue

        t0, az0, el0 = achieved_trajectory[achieved_idx]
        t1, az1, el1 = achieved_trajectory[achieved_idx + 1]

        if not (t0 <= desired_tai <= t1):
            mismatches.append(
                f"Desired TAI={desired_tai:.6f} out of interpolation bounds: {t0:.6f}-{t1:.6f}"
            )
            continue

        # Interpolate
        alpha = (desired_tai - t0) / (t1 - t0)
        interp_az = az0 + alpha * (az1 - az0)
        interp_el = el0 + alpha * (el1 - el0)

        angular_err = get_angular_error_between_points(
            desired_az, desired_el, interp_az, interp_el
        )

        err_tai_list.append(desired_tai)
        err_angular_list.append(angular_err)

        if angular_err > pointing_tolerance_arcsec:
            mismatches.append(
                f"Mismatch at TAI={desired_tai:.6f}:"
                f" desired ({desired_az:.6f}, {desired_el:.6f}),"
                f" interpolated ({interp_az:.6f}, {interp_el:.6f})"
                f" err=({angular_err:.6f})"
            )

    return mismatches, err_tai_list, err_angular_list


def setup_subscriptions(
    device_proxy: tango.DeviceProxy,
    attr_callback_map: Dict[str, EventStore],
    event_type: tango.EventType = tango.EventType.CHANGE_EVENT,
    reset_queue: bool = True,
) -> Dict[tango.DeviceProxy, List[int]]:
    """Subscribe to events for the given attributes and callbacks.

    :param device_proxy: The Tango device proxy.
    :param attr_callback_map: Dict mapping attribute names to EventStore callbacks.
    :param event_type: The Tango event type to subscribe to.
    :param reset_queue: Whether to clear the queue of each callback after subscribing.
    :return: Dict mapping device_proxy to list of subscription IDs.
    """
    sub_ids = []
    for attr, callback in attr_callback_map.items():
        sub_id = device_proxy.subscribe_event(
            attr,
            event_type,
            callback,
        )
        sub_ids.append(sub_id)
        # clear the queue if the callback has a clear_queue method
        if hasattr(callback, "clear_queue") and reset_queue:
            callback.clear_queue()
    return {device_proxy: sub_ids}


def remove_subscriptions(subscriptions: Dict[tango.DeviceProxy, List[int]]) -> None:
    """Unsubscribe from events for the given device proxy."""
    for device_proxy, subscription_ids in subscriptions.items():
        for sub_id in subscription_ids:
            try:
                device_proxy.unsubscribe_event(sub_id)
            except Exception:
                continue
