"""This module contains TangoDeviceMonitor that monitors attributes on Tango devices
If an error event is recieved the DeviceProxy and subscription will be recreated
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from functools import partial
from queue import Queue
from threading import Event, Lock
from typing import Callable, List

import tango
from ska_control_model import CommunicationStatus

SLEEP_BETWEEN_RECONNECTS = 0.5


class ReceivedErrorEvent(Exception):
    """Exception for error event"""


# pylint:disable=too-few-public-methods, too-many-instance-attributes
class TangoDeviceMonitor:
    """Connects to and monitor a Tango device.
    One thread per attribute.
    Each thread creates a DeviceProxy and subscibes to an attribute
    """

    # pylint:disable=too-many-arguments
    def __init__(
        self,
        tango_fqdn: str,
        monitored_attributes: List[str],
        event_queue: Queue,
        logger: logging.Logger,
        update_communication_state_cb: Callable,
    ) -> None:
        """Create the TangoDeviceMonitor

        :param tango_fqdn: Tango device name
        :type tango_fqdn: str
        :param monitored_attributes: List of attributes to monitor
        :type monitored_attributes: List[str]
        :param event_queue: Queue where events are sent
        :type event_queue: Queue
        :param logger: logger
        :type logger: logging.Logger
        :param update_communication_state_cb: Called when communication state changes
        :type update_communication_state_cb: Callable
        """
        self._tango_fqdn = tango_fqdn
        self._monitored_attributes = monitored_attributes
        self._event_queue = event_queue
        self._executor = None
        self._logger = logger

        self._exit_thread_event = None
        self._run_count = 0
        self._thread_futures = []
        self._update_communication_state_cb = update_communication_state_cb
        self._update_comm_state_lock = Lock()

    def monitor(self):
        """Kick off device monitoring

        This method is idempotent. When called the existing (if any)
        monitoring threads are removed and recreated.
        """
        self._run_count += 1
        if self._executor:
            # Clear out existing subscriptions
            self._exit_thread_event.set()
            self._executor.shutdown(wait=True)

        self._logger.info("Setting up monitoring on %s", self._tango_fqdn)
        self._executor = ThreadPoolExecutor(
            max_workers=len(self._monitored_attributes),
            thread_name_prefix=f"Monitoring_{self._run_count}_run",
        )
        self._logger.info("Monitoring thread pool started for %s", self._tango_fqdn)
        self._exit_thread_event = Event()
        self._thread_futures.clear()

        for attribute_name in self._monitored_attributes:
            future = self._executor.submit(
                self._monitor_attribute,
                self._tango_fqdn,
                attribute_name,
                self._exit_thread_event,
                self._event_queue,
                self._logger,
                self._update_communication_state_cb,
                self._update_comm_state_lock,
            )

            # Quick check for any basic errors
            try:
                exc = future.exception(0.1)
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
        update_communication_state_cb: Callable,
        update_comm_state_lock: Lock,
    ):
        """Monitor an attribute

        :param tango_fqdn: The Tango device name
        :type tango_fqdn: str
        :param attribute_name: The attribute to monitor
        :type attribute_name: str
        :param exit_thread_event: Signals when to exit the thread
        :type exit_thread_event: Event
        :param event_queue: Where non error events will be added
        :type event_queue: Queue
        :param logger: logger
        :type logger: logging.Logger
        :param update_communication_state_cb: Callback called when the connection changes
        :type update_communication_state_cb: Callable
        :param update_comm_state_lock: Make sure update_communication_state_cb is called
            sequentially
        :type update_comm_state_lock: Lock
        :raises ReceivedErrorEvent: Raised when an error event has been recieved
            The DeviceProxy and subscription is recreated
        """
        retry_count = 0
        with tango.EnsureOmniThread():

            def _event_reaction(event_queue, tango_event):
                if tango_event.err:
                    raise ReceivedErrorEvent(tango_event)
                event_queue.put(tango_event)

            while not exit_thread_event.is_set():
                with update_comm_state_lock:
                    update_communication_state_cb(CommunicationStatus.NOT_ESTABLISHED)
                try:
                    device_proxy = tango.DeviceProxy(tango_fqdn)
                    device_proxy.ping()
                    event_reaction_cb = partial(_event_reaction, event_queue)
                    subscription_id = device_proxy.subscribe_event(
                        attribute_name,
                        tango.EventType.CHANGE_EVENT,
                        event_reaction_cb,
                    )
                    logger.error("Subscribed on %s to attr %s", tango_fqdn, attribute_name)
                    with update_comm_state_lock:
                        update_communication_state_cb(CommunicationStatus.ESTABLISHED)
                    while not exit_thread_event.wait(1):
                        pass
                    device_proxy.unsubscribe_event(subscription_id)
                    logger.error("Unsubscribed from %s for attr %s", tango_fqdn, attribute_name)
                    subscription_id = None
                except tango.DevFailed as err:
                    logger.error(
                        "Tango error on %s for attr %s, try number %s",
                        tango_fqdn,
                        attribute_name,
                        retry_count,
                    )
                    logger.exception(err)
                    retry_count += 1
                    exit_thread_event.wait(SLEEP_BETWEEN_RECONNECTS)
                except ReceivedErrorEvent as err:
                    logger.error(
                        "Error event received on %s for attr %s, try number %s",
                        tango_fqdn,
                        attribute_name,
                        retry_count,
                    )
                    logger.exception(err)
                    retry_count += 1
                    exit_thread_event.wait(SLEEP_BETWEEN_RECONNECTS)
                except Exception as err:  # pylint: disable=W0703
                    logger.error(
                        "Error on %s for attr %s, try number %s",
                        tango_fqdn,
                        attribute_name,
                        retry_count,
                    )
                    logger.exception(err)
                    retry_count += 1
                    exit_thread_event.wait(SLEEP_BETWEEN_RECONNECTS)
