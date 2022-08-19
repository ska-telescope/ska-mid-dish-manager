# pylint: disable=invalid-name
"""General utils for test devices"""
import queue
import random
import time
from functools import wraps
from typing import Any, List, Tuple

import tango

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    BandInFocus,
    DishMode,
    IndexerPosition,
)


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
                if event.attr_value.value != value:
                    continue
                if event.attr_value.value == value:
                    return True
        except queue.Empty as err:
            ev_vals = self.extract_event_values(events)
            raise RuntimeError(
                f"Never got an event with value [{value}] got [{ev_vals}]"
            ) from err

    # pylint:disable=inconsistent-return-statements
    def wait_for_command_result(
        self, command_id: str, command_result: Any, timeout: int = 5
    ):
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
            raise RuntimeError(
                f"Never got an LRC result from command [{command_id}]"
            ) from err

    def wait_for_command_id(self, command_id: str, timeout: int = 5):
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
                if (
                    command_id == lrc_id
                    and event.attr_value.name == "longrunningcommandresult"
                ):
                    return events
        except queue.Empty as err:
            event_info = [
                (event.attr_value.name, event.attr_value.value)
                for event in events
            ]
            raise RuntimeError(
                f"Never got an LRC result from command [{command_id}],",
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
        return [
            event
            for event in events
            if unique_id in str(event.attr_value.value)
        ]

    def wait_for_n_events(self, event_count: int, timeout: int = 5):
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
    def extract_event_values(
        cls, events: List[tango.EventData]
    ) -> List[Tuple]:
        """Get the values out of events

        :param events: List of events
        :type events: List[tango.EventData]
        :return: List of value tuples
        :rtype: List[Tuple]
        """
        event_info = [
            (event.attr_value.name, event.attr_value.value, event.device)
            for event in events
        ]
        return event_info

    def get_queue_values(self, timeout: int = 3):
        items = []
        try:
            while True:
                event = self._queue.get(timeout=timeout)
                items.append((event.attr_value.name, event.attr_value.value))
        except queue.Empty:
            return items

    @classmethod
    def get_data_from_events(
        cls, events: List[tango.EventData]
    ) -> List[Tuple]:
        """Retrieve the event info from the events

        :param events: list of
        :type events: List[tango.EventData]
        """
        return [
            (event.attr_value.name, event.attr_value.value) for event in events
        ]


def random_delay_execution(func):
    """Delay a command a bit"""

    @wraps(func)
    def inner(*args, **kwargs):
        time.sleep(round(random.uniform(1.5, 2.5), 2))
        return func(*args, **kwargs)

    return inner


def set_dish_manager_to_standby_lp(event_store, dish_manager_proxy):
    """Ensure dishManager is in a known state"""
    if dish_manager_proxy.dishMode != DishMode.STANDBY_LP:

        dish_manager_proxy.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        # Set it to a known mode, can Stow from any state
        if dish_manager_proxy.dishMode != DishMode.STOW:
            dish_manager_proxy.SetStowMode()
            event_store.wait_for_value(DishMode.STOW, timeout=10)

        dish_manager_proxy.SetStandbyLPMode()
        event_store.wait_for_value(DishMode.STANDBY_LP, timeout=10)


def set_configuredBand_b1():
    """
    Set B1 configuredBand
    Rules:
        DS.indexerposition  == 'IndexerPosition.B1'
        SPFRX.configuredband  == 'Band.B1'
        SPF.bandinfocus == 'BandInFocus.B1'
    """
    ds_device = tango.DeviceProxy("mid_d0001/lmc/ds_simulator")
    spf_device = tango.DeviceProxy("mid_d0001/spf/simulator")
    spfrx_device = tango.DeviceProxy("mid_d0001/spfrx/simulator")

    ds_device.indexerPosition = IndexerPosition.B1
    spf_device.bandinfocus = BandInFocus.B1
    spfrx_device.configuredband = Band.B1


def set_configuredBand_b2():
    """
    Set B2 configuredBand
    Rules:
        DS.indexerposition  == 'IndexerPosition.B2'
        SPFRX.configuredband  == 'Band.B2'
        SPF.bandinfocus == 'BandInFocus.B2'
    """
    ds_device = tango.DeviceProxy("mid_d0001/lmc/ds_simulator")
    spf_device = tango.DeviceProxy("mid_d0001/spf/simulator")
    spfrx_device = tango.DeviceProxy("mid_d0001/spfrx/simulator")

    ds_device.indexerPosition = IndexerPosition.B2
    spf_device.bandinfocus = BandInFocus.B2
    spfrx_device.configuredband = Band.B2
