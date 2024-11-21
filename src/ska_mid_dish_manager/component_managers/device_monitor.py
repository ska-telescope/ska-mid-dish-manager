"""This module contains TangoDeviceMonitor that monitors attributes on Tango devices
If an error event is received the DeviceProxy and subscription will be recreated
"""

import logging
from functools import partial
from queue import Queue
from threading import Event, Lock, Thread
from typing import Any, Callable, Tuple

import tango
from ska_control_model import CommunicationStatus

TEST_CONNECTION_PERIOD = 2
SLEEP_BETWEEN_EVENTS = 0.5


class SubscriptionTracker:
    """Thread safe way to track which attributes are subscribed"""

    def __init__(
        self,
        monitored_attributes: Tuple[str, ...],
        update_communication_state: Callable,
        logger: logging.Logger,
    ):
        """Keep track of which attributes has been subscribed to.

        Set communication_state to ESTABLISHED only when all are subscribed.
        Set NOT_ESTABLISHED otherwise.

        :param monitored_attributes: The attribute names to monitor
        :type monitored_attributes: Tuple[str, ...]
        :param update_communication_state: Update communication status
        :type update_communication_state: Callable
        :param update_communication_state: Logger
        :type update_communication_state: logging.Logger
        """
        self._monitored_attributes = monitored_attributes
        self._update_communication_state = update_communication_state
        self._logger = logger
        self._subscribed_attrs = dict.fromkeys(self._monitored_attributes, False)
        self._update_lock = Lock()

    def subscription_started(self, attribute_name: str) -> None:
        """Mark attr as subscribed

        :param attribute_name: The attribute name
        :type attribute_name: str
        """
        with self._update_lock:
            self._logger.info("Marking %s attribute as subscribed", attribute_name)
            self._subscribed_attrs[attribute_name] = True
            self.update_subscription_status()

    def subscription_stopped(self, attribute_name: str) -> None:
        """Mark attr as unsubscribed

        :param attribute_name: The attribute name
        :type attribute_name: str
        """
        with self._update_lock:
            self._logger.info("Marking %s attribute as not subscribed", attribute_name)
            self._subscribed_attrs[attribute_name] = False
            self.update_subscription_status()

    def clear_subscriptions(self) -> None:
        """Set all attrs as not subscribed"""
        with self._update_lock:
            for key in self._subscribed_attrs:
                self._subscribed_attrs[key] = False
            self.update_subscription_status()

    def all_subscribed(self) -> bool:
        """Check if all attributes have been subscribed

        :return: all attributes subscribed
        :rtype: bool
        """
        return all(self._subscribed_attrs.values())

    def update_subscription_status(self) -> None:
        """Update Communication Status"""
        if self.all_subscribed():
            self._logger.info("Updating CommunicationStatus as ESTABLISHED")
            self._update_communication_state(CommunicationStatus.ESTABLISHED)
        else:
            self._logger.info("Updating CommunicationStatus as NOT_ESTABLISHED")
            self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)


# pylint:disable=too-few-public-methods, too-many-instance-attributes
class TangoDeviceMonitor:
    """Connects to and monitor a Tango device.
    One thread per attribute.
    Each thread creates a DeviceProxy and subscribes to an attribute
    """

    # pylint:disable=too-many-arguments
    def __init__(
        self,
        trl: str,
        monitored_attributes: Tuple[str, ...],
        event_queue: Queue,
        logger: logging.Logger,
        update_communication_state: Callable,
    ) -> None:
        """Create the TangoDeviceMonitor

        :param: trl: Tango device name
        :type trl: str
        :param monitored_attributes: Tuple of attributes to monitor
        :type monitored_attributes: Tuple[str]
        :param event_queue: Queue where events are sent
        :type event_queue: Queue
        :param logger: logger
        :type logger: logging.Logger
        """
        self._trl = trl
        self._monitored_attributes = monitored_attributes
        self._event_queue = event_queue
        self._logger = logger
        self._run_count = 0
        self._exit_thread_event: Event = Event()
        # pylint: disable=bad-thread-instantiation
        self._start_monitoring_thread: Thread = Thread()

        self._subscription_tracker = SubscriptionTracker(
            self._monitored_attributes, update_communication_state, self._logger
        )

    def stop_monitoring(self) -> None:
        """Close all the monitroing threads"""
        self._subscription_tracker.clear_subscriptions()
        self._logger.info("Stopped monitoring thread on %s", self._trl)

        # Stop any existing start monitoring thread
        if self._start_monitoring_thread.is_alive():
            self._exit_thread_event.set()
            self._start_monitoring_thread.join()

    def _verify_connection_up(
        self, on_verified_callback: Callable, exit_thread_event: Event
    ) -> None:
        """
        Verify connection to the device by pinging it
        Starts attribute monitoring threads once the connection is verified

        :param on_verified_callback: Callback for when connection is verified
        :type on_verified_callback: Callable
        :param exit_thread_event: Signals when to exit the thread
        :type exit_thread_event: Event
        """
        self._logger.info("Check %s is up", self._trl)
        try_count = 0

        while not exit_thread_event.is_set():
            try:
                with tango.EnsureOmniThread():
                    proxy = tango.DeviceProxy(self._trl)
                    proxy.ping()
                on_verified_callback(exit_thread_event)
                return
            except tango.DevFailed:
                self._logger.info("Cannot connect to %s try number %s", self._trl, try_count)
                try_count += 1
                exit_thread_event.wait(TEST_CONNECTION_PERIOD)

    def monitor(self) -> None:
        """Kick off device monitoring

        This method is idempotent. When called the existing (if any)
        monitoring threads are removed and recreated.
        """
        self._run_count += 1

        if self._start_monitoring_thread.is_alive():
            self.stop_monitoring()

        self._exit_thread_event = Event()

        self._start_monitoring_thread = Thread(
            target=self._verify_connection_up,
            args=[
                self._monitor_attributes_single_thread,
                self._exit_thread_event,
            ],  # start one thread to monitor all attributes
        )
        self._start_monitoring_thread.start()

    # pylint:disable=too-many-arguments
    def _monitor_attributes_single_thread(self, exit_thread_event: Event) -> None:
        """Monitor all attributes

        :param exit_thread_event: Signals when to exit the thread
        :type exit_thread_event: Event
        """
        self._logger.info("Setting up monitoring on %s", self._trl)

        with tango.EnsureOmniThread():
            retry_counts = {name: 0 for name in self._monitored_attributes}
            subscriptions = {name: None for name in self._monitored_attributes}

            def _event_reaction(events_queue: Queue, tango_event: tango.EventData) -> None:
                events_queue.put(tango_event)

            # set up all subscriptions
            device_proxy = None
            while not exit_thread_event.is_set():
                try:
                    device_proxy = tango.DeviceProxy(self._trl)
                    device_proxy.ping()

                    # Subscribe to all monitored attributes
                    for attribute_name in self._monitored_attributes:
                        if exit_thread_event.is_set():
                            return

                        event_reaction_cb = partial(_event_reaction, self._event_queue)

                        subscription_id = device_proxy.subscribe_event(
                            attribute_name,
                            tango.EventType.CHANGE_EVENT,
                            event_reaction_cb,
                        )
                        subscriptions[attribute_name] = subscription_id
                        self._subscription_tracker.subscription_started(attribute_name)

                        self._logger.info("Subscribed on %s to attr %s", self._trl, attribute_name)

                    self._logger.info("Monitoring threads started for %s", self._trl)

                    # Thread will wait here for events to happen
                    while not exit_thread_event.wait(SLEEP_BETWEEN_EVENTS):
                        pass
                except tango.DevFailed:
                    self._logger.exception(
                        (
                            f"Tango error on {self._trl} for attr {attribute_name}, "
                            f"try number {retry_counts[attribute_name]}"
                        )
                    )
                    retry_counts[attribute_name] += 1
                except Exception:  # pylint: disable=W0703
                    self._logger.exception(
                        (
                            f"Error on {self._trl} for attr {attribute_name}, "
                            f"try number {retry_counts[attribute_name]}"
                        )
                    )
                    retry_counts[attribute_name] += 1

                # Try and clean up the subscription, probably not possible
                for attribute_name in self._monitored_attributes:
                    try:
                        if device_proxy is not None and subscriptions[attribute_name] is not None:
                            device_proxy.unsubscribe_event(subscriptions[attribute_name])
                            self._logger.info(
                                "Unsubscribed from %s for attr %s",
                                self._trl,
                                attribute_name,
                            )

                            subscriptions[attribute_name] = None
                        self._subscription_tracker.subscription_stopped(attribute_name)
                    except tango.DevFailed as err:
                        self._logger.exception(err)
                        self._logger.info(
                            "Could not unsubscribe from %s for attr %s",
                            self._trl,
                            attribute_name,
                        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    def empty_func(*args: Any, **kwargs: Any) -> None:  # pylint: disable=unused-argument
        """An empty function"""
        pass  # pylint:disable=unnecessary-pass

    tdm = TangoDeviceMonitor(
        "tango://localhost:45678/mid-dish/simulator-spf/ska001#dbase=no",
        ("powerState",),
        Queue(),
        logging.getLogger(__name__),
        empty_func,
    )
    tdm.monitor()
