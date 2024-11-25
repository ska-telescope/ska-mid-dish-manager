"""
This module contains TangoDeviceMonitor that monitors attributes on Tango devices
"""

import logging
from functools import partial
from queue import Queue
from threading import Event, Lock, Thread
from typing import Any, Callable, Dict, Optional, Tuple

import tango

from ska_mid_dish_manager.component_managers.device_proxy_factory import DeviceProxyManager

RETRY_TIME = 2
SLEEP_BETWEEN_EVENTS = 0.5


class SubscriptionTracker:
    """Thread safe way to track which attributes are subscribed"""

    def __init__(
        self,
        event_queue: Queue,
        logger: logging.Logger,
        subscription_status_callback: Optional[Callable] = None,
    ):
        """
        Keep track of which attributes has been subscribed to.

        Set communication_state to ESTABLISHED only when all are subscribed.
        Set NOT_ESTABLISHED otherwise.

        :param event_queue: the store for change events emitted by the device
        :type event_queue: Queue
        :param logger: Logger
        :type logger: logging.Logger
        :param subscription_status_callback: Update communication status based on the subscription
        :type subscription_status_callback: Callable
        """
        self._event_queue = event_queue
        self.subscription_status_callback = subscription_status_callback
        self._logger = logger
        self._subscribed_attrs: Dict[str, int] = {}
        self._update_lock = Lock()

    @property
    def subscribed_attrs(self) -> list:
        """
        Get the list of attributes with change events

        :return: list of attribute names
        """
        return list(self._subscribed_attrs.keys())

    def subscription_started(self, attribute_name: str, subscription_id: int) -> None:
        """
        Mark attr as subscribed

        :param attribute_name: The attribute name
        :type attribute_name: str
        :param subscription_id: The subscription descriptor
        :type subcription_id: int
        """
        with self._update_lock:
            self._subscribed_attrs[attribute_name] = subscription_id
        if self.subscription_status_callback:
            self.subscription_status_callback(self._subscribed_attrs.keys())

    def subscription_stopped(self, attribute_name: str) -> None:
        """
        Mark attr as unsubscribed

        :param attribute_name: The attribute name
        :type attribute_name: str
        """
        with self._update_lock:
            self._subscribed_attrs.pop(attribute_name)
        if self.subscription_status_callback:
            self.subscription_status_callback(self._subscribed_attrs.keys())

    def setup_event_subscription(
        self, attribute_name: str, device_proxy: tango.DeviceProxy
    ) -> None:
        """
        Subscribe to change events on the device
        """
        # dont subscribe to attributes with live subscriptions already
        if attribute_name in self._subscribed_attrs:
            return

        def _event_reaction(events_queue: Queue, tango_event: tango.EventData) -> None:
            events_queue.put(tango_event)

        event_reaction_cb = partial(_event_reaction, self._event_queue)
        with tango.EnsureOmniThread():
            try:
                subscription_id = device_proxy.subscribe_event(
                    attribute_name,
                    tango.EventType.CHANGE_EVENT,
                    event_reaction_cb,
                )
            except tango.EventSystemFailed as err:
                raise err
            self._logger.debug(
                "Subscribed to attr %s on %s", attribute_name, device_proxy.dev_name()
            )

        self.subscription_started(attribute_name, subscription_id)

    def clear_subscriptions(self, device_proxy: tango.DeviceProxy) -> None:
        """
        Set all attrs as not subscribed
        """
        # subscription stopped will update the dictionary being iterated over
        # and raise a RuntimeError. grab a copy to use in the iteration
        subscribed_attrs_copy = self._subscribed_attrs.copy()
        with tango.EnsureOmniThread():
            for attribute_name, subscription_id in subscribed_attrs_copy.items():
                try:
                    device_proxy.unsubscribe_event(subscription_id)
                    self._logger.debug(
                        "Unsubscribed from %s attr on %s",
                        attribute_name,
                        device_proxy.dev_name(),
                    )
                except tango.EventSystemFailed:
                    self._logger.exception(
                        "Could not unsubscribe from %s attr on %s",
                        attribute_name,
                        device_proxy.dev_name(),
                    )
                else:
                    self.subscription_stopped(attribute_name)


# pylint:disable=too-few-public-methods, too-many-instance-attributes
class TangoDeviceMonitor:
    """
    Connects to and monitors a Tango device.

    Creates a device proxy in a thread to subscribe to change events on specified attributes
    """

    # pylint:disable=too-many-arguments
    def __init__(
        self,
        tango_fqdn: str,
        device_proxy_factory: DeviceProxyManager,
        monitored_attributes: Tuple[str, ...],
        event_queue: Queue,
        logger: logging.Logger,
        subscription_status_callback: Optional[Callable] = None,
    ) -> None:
        """
        Create the TangoDeviceMonitor.

        :param: tango_fqdn: Tango device name
        :type tango_fqdn: str
        :param device_proxy_factory: A factory which creates and manages tango device proxies
        :type device_proxy_factory: DeviceProxyManager
        :param monitored_attributes: Tuple of attributes to monitor
        :type monitored_attributes: Tuple[str]
        :param event_queue: Queue where events are sent
        :type event_queue: Queue
        :param logger: logger
        :type logger: logging.Logger
        :param subscription_status_callback: Sync communication to subscription
        :type subscription_status_callback: Callable
        """
        self._tango_fqdn = tango_fqdn
        self._device_proxy_factory = device_proxy_factory
        self._monitored_attributes = monitored_attributes
        self._event_queue = event_queue
        self._logger = logger
        self._run_count = 0
        self._exit_thread_event: Optional[Event] = None
        self._attribute_subscription_thread: Optional[Thread] = None

        self._subscription_tracker = SubscriptionTracker(
            self._event_queue, self._logger, subscription_status_callback
        )

    def stop_monitoring(self) -> None:
        """Close all live attribute subscriptions"""
        if (
            self._attribute_subscription_thread is not None
            and self._exit_thread_event is not None
            and self._attribute_subscription_thread.is_alive()
        ):
            # Stop any existing thread performing attribute event subscriptions
            self._exit_thread_event.set()
            self._attribute_subscription_thread.join()
            self._logger.info("Stopped monitoring thread on %s", self._tango_fqdn)
            # undo subscriptions and inform client we have no comms to the device
            if self._subscription_tracker.subscribed_attrs:
                device_proxy = self._device_proxy_factory(self._tango_fqdn)
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
        self._logger.info("Check %s is up", self._tango_fqdn)

        while not exit_thread_event.is_set():
            dev_proxy = self._device_proxy_factory(self._tango_fqdn)
            if dev_proxy:
                on_verified_callback(exit_thread_event)
                return

    def monitor(self) -> None:
        """
        Kick off device monitoring

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

        self._attribute_subscription_thread.name = f"{self._tango_fqdn}_attribute_subscription_thread"
        # monitor all attributes in a thread
        self._attribute_subscription_thread.start()

    # pylint:disable=too-many-arguments
    def _monitor_attributes_in_a_thread(self, exit_thread_event: Event) -> None:
        """
        Monitor all attributes

        :param exit_thread_event: Signals when to exit the thread
        :type exit_thread_event: Event
        """
        self._logger.info("Setting up monitoring on %s", self._tango_fqdn)

        retry_counts = {name: 1 for name in self._monitored_attributes}
        # set up all subscriptions
        device_proxy = self._device_proxy_factory(self._tango_fqdn)
        while not exit_thread_event.is_set():
            try:
                # Subscribe to all monitored attributes
                for attribute_name in self._monitored_attributes:
                    if exit_thread_event.is_set():
                        return

                    self._subscription_tracker.setup_event_subscription(
                        attribute_name, device_proxy
                    )

                self._logger.info(
                    "Change event subscriptions on %s successfully set up for %s",
                    self._tango_fqdn,
                    self._monitored_attributes,
                )

                # Keep thread alive while the events are being processed
                while not exit_thread_event.wait(timeout=SLEEP_BETWEEN_EVENTS):
                    pass
            except tango.DevFailed:
                self._logger.exception(
                    (
                        f"Encountered tango error on {self._tango_fqdn} for {attribute_name} "
                        f"attribute subscription, try number {retry_counts[attribute_name]}"
                    )
                )
                retry_counts[attribute_name] += 1
                exit_thread_event.wait(timeout=RETRY_TIME)
            except Exception:  # pylint: disable=W0703
                self._logger.exception(
                    (
                        f"Encountered python error on {self._tango_fqdn} for {attribute_name} "
                        f"attribute subscription, try number {retry_counts[attribute_name]}"
                    )
                )
                retry_counts[attribute_name] += 1
                exit_thread_event.wait(timeout=RETRY_TIME)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    signal = Event()
    basic_logger = logging.getLogger(__name__)

    def empty_func(*args: Any, **kwargs: Any) -> None:  # pylint: disable=unused-argument
        """An empty function"""
        pass  # pylint:disable=unnecessary-pass

    tdm = TangoDeviceMonitor(
        "tango://localhost:45678/mid-dish/simulator-spf/ska001#dbase=no",
        DeviceProxyManager(basic_logger, signal),
        ("powerState",),
        Queue(),
        basic_logger,
        empty_func,
    )
    tdm.monitor()
