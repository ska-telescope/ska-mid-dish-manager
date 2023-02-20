"""This module contains TangoDeviceMonitor that monitors attributes on Tango devices
If an error event is received the DeviceProxy and subscription will be recreated
"""
import logging
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from functools import partial
from queue import Queue
from threading import Event, Lock, Thread
from typing import Callable, List, Optional, Tuple

import tango
from ska_control_model import CommunicationStatus

from ska_mid_dish_manager.models.dish_mode_model import PrioritizedEventData

TEST_CONNECTION_PERIOD = 2
SLEEP_BETWEEN_EVENTS = 0.5


# pylint:disable=too-few-public-methods, too-many-instance-attributes
class TangoDeviceMonitor:
    """Connects to and monitor a Tango device.
    One thread per attribute.
    Each thread creates a DeviceProxy and subscribes to an attribute
    """

    # pylint:disable=too-many-arguments
    def __init__(
        self,
        tango_fqdn: str,
        monitored_attributes: Tuple[str, ...],
        event_queue: Queue,
        logger: logging.Logger,
        update_communication_state: Callable,
    ) -> None:
        """Create the TangoDeviceMonitor

        :param: tango_fqdn: Tango device name
        :type tango_fqdn: str
        :param monitored_attributes: Tuple of attributes to monitor
        :type monitored_attributes: Tuple[str]
        :param event_queue: Queue where events are sent
        :type event_queue: Queue
        :param logger: logger
        :type logger: logging.Logger
        """
        self._tango_fqdn = tango_fqdn
        self._monitored_attributes = monitored_attributes
        self._event_queue = event_queue
        self._logger = logger
        self._update_communication_state = update_communication_state

        self._executor: Optional[ThreadPoolExecutor] = None
        self._run_count = 0
        self._update_comm_state_lock = Lock()
        self._thread_futures: List[Future] = []
        self._exit_thread_event: Event = Event()
        # pylint: disable=bad-thread-instantiation
        self._start_monitoring_thread: Thread = Thread()

    def stop_monitoring(self) -> None:
        """Close all the monitroing threads"""
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)

        # Stop any existing start monitoring thread
        if self._start_monitoring_thread.is_alive():
            self._exit_thread_event.set()
            self._start_monitoring_thread.join()

        # Clear out existing subscriptions
        if self._executor:
            self._exit_thread_event.set()
            self._logger.info("Stopping current monitoring threads on %s", self._tango_fqdn)
            self._executor.shutdown(wait=True, cancel_futures=True)
            self._logger.info("Stopped monitoring threads on %s", self._tango_fqdn)

    def _verify_connection_up(self, start_monitoring_threads: Callable) -> None:
        """
        Verify connection to the device by pinging it
        Starts attribute monitoring threads once the connection is verified
        """
        self._logger.info("Check %s is up", self._tango_fqdn)
        try_count = 0

        self._exit_thread_event = Event()

        while not self._exit_thread_event.is_set():
            try:
                proxy = tango.DeviceProxy(self._tango_fqdn)
                proxy.ping()
                return start_monitoring_threads()
            except tango.DevFailed:
                self._logger.info(
                    "Cannot connect to %s try number %s", self._tango_fqdn, try_count
                )
                try_count += 1
                self._exit_thread_event.wait(TEST_CONNECTION_PERIOD)

    def _start_monitoring_threads(self) -> None:
        """
        Starts a threadpool for monitoring attributes and submits
        a thread for each of the devices monitored attributes
        """
        self._logger.info("Setting up monitoring on %s", self._tango_fqdn)
        self._executor = ThreadPoolExecutor(
            max_workers=len(self._monitored_attributes),
            thread_name_prefix=f"Monitoring_run_{self._run_count}_attr_no_",
        )
        self._logger.info("Monitoring thread pool started for %s", self._tango_fqdn)
        self._thread_futures = []

        # Start attr monitoring threads
        for attribute_name in self._monitored_attributes:
            future = self._executor.submit(
                self._monitor_attribute,
                self._tango_fqdn,
                attribute_name,
                self._exit_thread_event,
                self._event_queue,
                self._logger,
            )
            self._thread_futures.append(future)

        for thread_future in self._thread_futures:
            # Quick check for any basic errors
            try:
                exc = thread_future.exception(0.1)
                if exc:
                    raise exc
            except FutureTimeoutError:
                # No error happened in time
                pass
        self._logger.info("Monitoring threads started for %s", self._tango_fqdn)
        self._update_communication_state(CommunicationStatus.ESTABLISHED)

    def monitor(self) -> None:
        """Kick off device monitoring

        This method is idempotent. When called the existing (if any)
        monitoring threads are removed and recreated.
        """
        self._run_count += 1

        if self._start_monitoring_thread.is_alive() or self._executor:
            self.stop_monitoring()

        self._start_monitoring_thread = Thread(
            target=self._verify_connection_up,
            args=[self._start_monitoring_threads],
        )
        self._start_monitoring_thread.start()

    # pylint:disable=too-many-arguments
    @classmethod
    def _monitor_attribute(
        cls,
        tango_fqdn: str,
        attribute_name: str,
        exit_thread_event: Event,
        event_queue: Queue,
        logger: logging.Logger,
    ) -> None:
        """Monitor an attribute

        :param: tango_fqdn: The Tango device name
        :type tango_fqdn: str
        :param attribute_name: The attribute to monitor
        :type attribute_name: str
        :param exit_thread_event: Signals when to exit the thread
        :type exit_thread_event: Event
        :param event_queue: Where non error events will be added
        :type event_queue: Queue
        :param logger: logger
        :type logger: logging.Logger
        """
        retry_count = 0
        subscription_id = None
        with tango.EnsureOmniThread():
            while not exit_thread_event.is_set():
                try:

                    def _event_reaction(events_queue: Queue, tango_event: tango.EventData) -> None:
                        if tango_event.err:
                            logger.info("Got an error event on %s %s", tango_fqdn, tango_event)
                            events_queue.put(PrioritizedEventData(priority=2, item=tango_event))
                        else:
                            events_queue.put(PrioritizedEventData(priority=1, item=tango_event))

                    device_proxy = tango.DeviceProxy(tango_fqdn)
                    device_proxy.ping()
                    if exit_thread_event.is_set():
                        return
                    event_reaction_cb = partial(_event_reaction, event_queue)
                    subscription_id = device_proxy.subscribe_event(
                        attribute_name,
                        tango.EventType.CHANGE_EVENT,
                        event_reaction_cb,
                    )
                    logger.info("Subscribed on %s to attr %s", tango_fqdn, attribute_name)
                    if exit_thread_event.is_set():
                        return
                    # Most time spent here waiting for events
                    while not exit_thread_event.wait(SLEEP_BETWEEN_EVENTS):
                        pass
                except tango.DevFailed:
                    logger.exception(
                        (
                            f"Tango error on {tango_fqdn} for attr {attribute_name}, "
                            f"try number {retry_count}"
                        )
                    )
                    retry_count += 1
                except Exception:  # pylint: disable=W0703
                    logger.exception(
                        (
                            f"Error Tango {tango_fqdn} for attr {attribute_name},"
                            f" try number {retry_count}"
                        )
                    )
                    retry_count += 1

                # Try and clean up the subscription, probably not possible
                try:
                    if subscription_id:
                        device_proxy.unsubscribe_event(subscription_id)
                        logger.info("Unsubscribed from %s for attr %s", tango_fqdn, attribute_name)
                except tango.DevFailed as err:
                    logger.exception(err)
                    logger.info(
                        "Could not unsubscribe from %s for attr %s", tango_fqdn, attribute_name
                    )
