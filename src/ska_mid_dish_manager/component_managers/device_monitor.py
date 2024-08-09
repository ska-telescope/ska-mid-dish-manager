"""
This module contains TangoDeviceMonitor that monitors attributes on Tango devices
"""

import logging
from functools import partial
from queue import Queue
from threading import Event, Lock, Thread
from typing import Any, Callable, Tuple

import tango
from ska_control_model import CommunicationStatus

from ska_mid_dish_manager.component_managers.device_proxy_factory import DeviceProxyManager

RETRY_TIME = 2
SLEEP_BETWEEN_EVENTS = 0.5


class SubscriptionTracker:
    """Thread safe way to track which attributes are subscribed"""

    def __init__(
        self,
        event_queue: Queue,
        update_communication_state: Callable,
        logger: logging.Logger,
    ):
        """Keep track of which attributes has been subscribed to.

        Set communication_state to ESTABLISHED only when all are subscribed.
        Set NOT_ESTABLISHED otherwise.

        :param event_queue: the store for change events emitted by the device server
        :type event_queue: Queue
        :param update_communication_state: Update communication status
        :type update_communication_state: Callable
        :param logger: Logger
        :type logger: logging.Logger
        ...
        """
        self._event_queue = event_queue
        self._update_communication_state = update_communication_state
        self._logger = logger
        self._subscribed_attrs = {}
        self._update_lock = Lock()

    def subscription_started(self, attribute_name: str, subscription_id: int) -> None:
        """Mark attr as subscribed

        :param attribute_name: The attribute name
        :type attribute_name: str
        :param subscription_id: The subscription descriptor
        :type subcription_id: int
        """
        with self._update_lock:
            self._logger.info("Marking %s attribute as subscribed", attribute_name)
            self._subscribed_attrs[attribute_name] = subscription_id
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

    def setup_event_subscription(
        self, attribute_name: str, device_proxy: tango.DeviceProxy
    ) -> None:
        """Subscribe to change events on the device server"""

        def _event_reaction(events_queue: Queue, tango_event: tango.EventData) -> None:
            events_queue.put(tango_event)

        event_reaction_cb = partial(_event_reaction, self._event_queue)
        try:
            subscription_id = device_proxy.subscribe_event(
                attribute_name,
                tango.EventType.CHANGE_EVENT,
                event_reaction_cb,
            )
        except tango.DevFailed as err:
            raise err

        self.subscription_started(attribute_name, subscription_id)

    def clear_subscriptions(self, device_proxy: tango.DeviceProxy) -> None:
        """Set all attrs as not subscribed"""
        for attribute_name, subscription_id in self._subscribed_attrs.items():
            if self._subscribed_attrs.get(attribute_name) is not None:
                try:
                    device_proxy.unsubscribe_event(subscription_id)
                    self._logger.info(
                        "Unsubscribed from %s attr on %s",
                        attribute_name,
                        device_proxy.dev_name(),
                    )
                except tango.DevFailed as err:
                    self._logger.exception(err)
                    self._logger.info(
                        "Could not unsubscribe from %s attr on %s",
                        attribute_name,
                        device_proxy.dev_name(),
                    )
                self.subscription_stopped(attribute_name)

    # Do we want to tell the world we arent talking to the
    # sub system because we cant subscribe to an attr?
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
    """
    Connects to and monitors a Tango device.

    Creates a device proxy in a thread to subscribe to change events on specified attributes
    """

    # pylint:disable=too-many-arguments
    def __init__(
        self,
        trl: str,
        device_proxy_factory: DeviceProxyManager,
        monitored_attributes: Tuple[str, ...],
        event_queue: Queue,
        logger: logging.Logger,
        update_communication_state: Callable,
    ) -> None:
        """
        Create the TangoDeviceMonitor.

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
        self._tango_device_proxy = device_proxy_factory
        self._monitored_attributes = monitored_attributes
        self._event_queue = event_queue
        self._logger = logger

        self._run_count = 0
        self._exit_thread_event: Event = None
        self._attribute_subscription_thread: Thread = None

        self._subscription_tracker = SubscriptionTracker(
            self._event_queue, update_communication_state, self._logger
        )

    def stop_monitoring(self) -> None:
        """Close all live attribute subscriptions"""
        if self._attribute_subscription_thread:
            # Stop any existing thread with live event subscriptions
            if self._attribute_subscription_thread.is_alive():
                self._exit_thread_event.set()
                self._attribute_subscription_thread.join()
                self._logger.info("Stopped monitoring threads on %s", self._trl)
                # undo subscriptions and inform client we have no comms to the device server
                device_proxy = self._tango_device_proxy(self._trl)
                with tango.EnsureOmniThread():
                    self._subscription_tracker.clear_subscriptions(device_proxy)

    def _verify_connection_up(
        self, on_verified_callback: Callable, exit_thread_event: Event
    ) -> None:
        """
        Verify connection to the device by pinging it.
        Starts attribute monitoring thread once the connection is verified

        :param on_verified_callback: Callback for when connection is verified
        :type on_verified_callback: Callable
        :param exit_thread_event: Signals when to exit the thread
        :type exit_thread_event: Event
        """
        self._logger.info("Check %s is up", self._trl)

        while not exit_thread_event.is_set():
            if self._tango_device_proxy(self._trl):
                on_verified_callback(exit_thread_event)
            return

    def monitor(self) -> None:
        """Kick off device monitoring

        This method is idempotent. When called the existing (if any)
        monitoring threads are removed and recreated.
        """
        self._run_count += 1

        self.stop_monitoring()

        self._exit_thread_event = Event()

        self._attribute_subscription_thread = Thread(
            target=self._verify_connection_up,
            args=[
                self._monitor_attributes_in_a_thread,
                self._exit_thread_event,
            ],
        )
        # monitor all attributes in a thread
        self._attribute_subscription_thread.start()

    # pylint:disable=too-many-arguments
    def _monitor_attributes_in_a_thread(self, exit_thread_event: Event) -> None:
        """Monitor all attributes

        :param exit_thread_event: Signals when to exit the thread
        :type exit_thread_event: Event
        """
        self._logger.info("Setting up monitoring on %s", self._trl)

        retry_counts = {name: 0 for name in self._monitored_attributes}
        # set up all subscriptions
        while not exit_thread_event.is_set():
            device_proxy = self._tango_device_proxy(self._trl)
            with tango.EnsureOmniThread():
                try:
                    # Subscribe to all monitored attributes
                    for attribute_name in self._monitored_attributes:
                        if exit_thread_event.is_set():
                            return

                        self._subscription_tracker.setup_event_subscription(
                            attribute_name, device_proxy
                        )

                        self._logger.debug(
                            "Subscribed on %s to attr %s", self._trl, attribute_name
                        )

                    self._logger.info(
                        "Change event subscriptions on %s successfully set up for %s",
                        self._trl,
                        self._monitored_attributes,
                    )

                    # Keep thread alive while the events are being processed
                    # is this necessary?
                    while not exit_thread_event.wait(timeout=SLEEP_BETWEEN_EVENTS):
                        pass
                except tango.DevFailed:
                    self._logger.exception(
                        (
                            f"Encountered tango error on {self._trl} for {attribute_name} "
                            f"attribute subscription, try number {retry_counts[attribute_name]}"
                        )
                    )
                    retry_counts[attribute_name] += 1
                    exit_thread_event.wait(timeout=RETRY_TIME)
                except Exception:  # pylint: disable=W0703
                    self._logger.exception(
                        (
                            f"Encountered python error on {self._trl} for {attribute_name} "
                            f"attribute subscription, try number {retry_counts[attribute_name]}"
                        )
                    )
                    retry_counts[attribute_name] += 1
                    exit_thread_event.wait(timeout=RETRY_TIME)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    def empty_func(*args: Any, **kwargs: Any) -> None:  # pylint: disable=unused-argument
        """An empty function"""
        pass  # pylint:disable=unnecessary-pass

    basic_logger = (logging.getLogger(__name__),)
    tdm = TangoDeviceMonitor(
        "tango://localhost:45678/mid-dish/simulator-spf/ska001#dbase=no",
        DeviceProxyManager(basic_logger),
        ("powerState",),
        Queue(),
        basic_logger,
        empty_func,
    )
    tdm.monitor()
