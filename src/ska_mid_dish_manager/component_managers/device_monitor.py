"""This module contains TangoDeviceMonitor that monitors attributes on Tango devices
If an error event is received the DeviceProxy and subscription will be recreated
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from functools import partial
from queue import Queue
from threading import Event, Lock
from typing import Callable, Optional, Tuple

import tango
from ska_control_model import CommunicationStatus

SLEEP_BETWEEN_RECONNECTS = 1
TEST_CONNECTION_PERIOD = 1


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
        monitored_attributes: Tuple[str],
        event_queue: Queue,
        logger: logging.Logger,
        update_sub_communication_state_cb: Optional[Callable] = None,
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
        :param update_sub_communication_state_cb: Called when communication state changes
        :type update_sub_communication_state_cb: Callable
        """
        self._tango_fqdn = tango_fqdn
        self._monitored_attributes = monitored_attributes
        self._event_queue = event_queue
        self._executor = None
        self._logger = logger
        self._update_sub_communication_state_cb = update_sub_communication_state_cb

        self._exit_thread_event = None
        self._run_count = 0
        self._update_comm_state_lock = Lock()
        self._thread_futures = []

    def monitor(self):
        """Kick off device monitoring

        This method is idempotent. When called the existing (if any)
        monitoring threads are removed and recreated.
        """
        self._run_count += 1
        if self._executor:
            self._logger.info("Stopping current monitoring threads on %s", self._tango_fqdn)
            # Clear out existing subscriptions
            self._exit_thread_event.set()
            self._executor.shutdown(wait=True, cancel_futures=True)
            self._logger.info("Stopped monitoring threads on %s", self._tango_fqdn)

        self._logger.info("Setting up monitoring on %s", self._tango_fqdn)
        self._executor = ThreadPoolExecutor(
            max_workers=len(self._monitored_attributes) + 1,
            thread_name_prefix=f"Monitoring_run_{self._run_count}_attr_no_",
        )
        self._logger.info("Monitoring thread pool started for %s", self._tango_fqdn)
        self._exit_thread_event = Event()
        self._thread_futures = []

        # Start heartbeat thread
        future = self._executor.submit(
                self._device_heartbeat,
                self._tango_fqdn,
                self._exit_thread_event,
                self._update_sub_communication_state_cb
            )
        self._thread_futures.append(future)
        
        # Start attr monitoring threads
        for attribute_name in self._monitored_attributes:
            future = self._executor.submit(
                self._monitor_attribute,
                self._tango_fqdn,
                attribute_name,
                self._exit_thread_event,
                self._event_queue,
                self._logger,
                self._update_comm_state_lock,
                self._update_sub_communication_state_cb,
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

    # pylint:disable=too-many-arguments
    @classmethod
    def _monitor_attribute(
        cls,
        tango_fqdn: str,
        attribute_name: str,
        exit_thread_event: Event,
        event_queue: Queue,
        logger: logging.Logger,
        update_comm_state_lock: Lock,
        update_sub_communication_state_cb: Optional[Callable],
    ):
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
        :param update_sub_communication_state_cb: Callback called when the connection changes
        :type update_sub_communication_state_cb: Callable
        :param update_comm_state_lock: Make sure update_sub_communication_state_cb is called
            sequentially
        :type update_comm_state_lock: Lock
        """
        retry_count = 0
        with tango.EnsureOmniThread():
            while not exit_thread_event.is_set():
                # Not connnected by default
                with update_comm_state_lock:
                    if update_sub_communication_state_cb:
                        update_sub_communication_state_cb(CommunicationStatus.NOT_ESTABLISHED)
                try:

                    def _event_reaction(events_queue, tango_event):
                        if tango_event.err:
                            logger.error("Got an error event on %s %s", tango_fqdn, tango_event)
                        events_queue.put(tango_event)

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
                    with update_comm_state_lock:
                        if update_sub_communication_state_cb:
                            update_sub_communication_state_cb(CommunicationStatus.ESTABLISHED)
                    # Most time spent here waiting for events
                    while not exit_thread_event.wait(1):
                        pass
                    device_proxy.unsubscribe_event(subscription_id)
                    logger.error("Unsubscribed from %s for attr %s", tango_fqdn, attribute_name)
                    subscription_id = None
                except tango.DevFailed:
                    logger.exception(
                        (
                            f"Error on Tango {tango_fqdn} for attr {attribute_name}, "
                            f"try number {retry_count}"
                        )
                    )
                    retry_count += 1
                    exit_thread_event.wait(SLEEP_BETWEEN_RECONNECTS)
                except Exception:  # pylint: disable=W0703
                    logger.exception(
                        (
                            f"Error Tango {tango_fqdn} for attr {attribute_name},"
                            f" try number {retry_count}"
                        )
                    )
                    retry_count += 1
                    exit_thread_event.wait(SLEEP_BETWEEN_RECONNECTS)

            # If we exit the thread we are not committed
            with update_comm_state_lock:
                if update_sub_communication_state_cb:
                    update_sub_communication_state_cb(CommunicationStatus.NOT_ESTABLISHED)

    @classmethod
    def _device_heartbeat(
        cls,
        tango_fqdn: str,
        exit_thread_event: Event,
        update_sub_communication_state_cb: Callable
    ):
        """Polls the connection to the subservient device every TEST_CONNECTION_PERIOD

        :param tango_fqdn: The Tango device
        :type tango_fqdn: str
        :param exit_thread_event: The thread exit signal
        :type exit_thread_event: Event
        :param logger: The logger
        :type logger: logging.Logger
        :param update_sub_communication_state_cb: Update the connection status
        :type update_sub_communication_state_cb: Callable
        """
        while not exit_thread_event.is_set():
            try:
                device_proxy = tango.DeviceProxy(tango_fqdn)
                while not exit_thread_event.is_set():
                    device_proxy.ping()
                    update_sub_communication_state_cb(CommunicationStatus.ESTABLISHED)
                    exit_thread_event.wait(timeout=TEST_CONNECTION_PERIOD)
            except tango.DevFailed:
                update_sub_communication_state_cb(CommunicationStatus.NOT_ESTABLISHED)
                exit_thread_event.wait(timeout=TEST_CONNECTION_PERIOD)

    def stop_monitoring(self):
        """Stop all monitoring threads"""
        if self._exit_thread_event:
            self._exit_thread_event.set()

