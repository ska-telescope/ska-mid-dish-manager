"""Generic component manager for a subservient tango device."""

import logging
from threading import Event, Thread
from typing import Any, Tuple

import numpy as np
import tango
from ska_control_model import CommunicationStatus, TaskStatus
from ska_tango_base import type_hints
from ska_tango_base.base import BaseComponentManager
from ska_tango_base.callback_scheduler import CallbackScheduler, Queue

from ska_mid_dish_manager.component_managers.device_proxy_factory import DeviceProxyManager
from ska_mid_dish_manager.models.constants import OPERATOR_TAG
from ska_mid_dish_manager.utils.decorators import check_communicating


class TangoDeviceComponentManager(BaseComponentManager):
    """A component manager for a Tango device."""

    def __init__(
        self,
        tango_device_fqdn: str,
        logger: logging.Logger,
        monitored_attributes: Tuple[str, ...],
        *args: Any,
        communication_state_callback: Any = None,
        component_state_callback: Any = None,
        quality_state_callback: Any = None,
        quality_monitored_attributes: Tuple[str, ...] = (),
        **kwargs: Any,
    ):
        self._quality_state_callback = quality_state_callback
        self._tango_device_fqdn = tango_device_fqdn
        self._monitored_attributes = tuple(attr.lower() for attr in monitored_attributes)
        self._quality_monitored_attributes = tuple(
            attr.lower() for attr in quality_monitored_attributes
        )
        self._active_attr_event_subscriptions: set[str] = set()
        self.logger = logger
        self._dp_factory_signal: Event = Event()

        self._device_proxy_factory = DeviceProxyManager(self.logger, self._dp_factory_signal)
        self._connection_thread: Thread | None = None
        self._events_monitor: CallbackScheduler | None = None

        # make sure everything monitored is in the component state
        attr_names_lower = map(lambda x: x.lower(), monitored_attributes)
        attrs_to_be_added = set(attr_names_lower).difference(kwargs.keys())
        kwargs.update(dict.fromkeys(attrs_to_be_added))

        # Ensure `buildstate` is present for buildState refresh logic.
        # If provided by caller, keep it; if missing (or explicitly None), default to empty.
        if kwargs.get("buildstate") is None:
            kwargs["buildstate"] = ""

        super().__init__(
            logger,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            **kwargs,
        )

    # ---------
    # Callbacks
    # ---------

    def _update_state_from_event(self, event_data: tango.EventData) -> None:
        """Update component state as the change events come in.

        :param event_data: Tango event
        :type event_data: tango.EventData
        """
        # I get lowercase and uppercase "State" from events
        # for some reason, stick to lowercase to avoid duplicates
        attr_name = event_data.attr_value.name.lower()
        quality = event_data.attr_value.quality
        try:
            if attr_name in self._quality_monitored_attributes:
                self._quality_state_callback(attr_name, quality)
        except Exception:  # pylint:disable=broad-except
            self.logger.exception("Error occurred on attribute quality state update")

        if quality is not tango.AttrQuality.ATTR_INVALID:
            try:
                value = event_data.attr_value.value
                if isinstance(value, np.ndarray):
                    value = list(value)
                self._update_component_state(**{attr_name: value})
            # Catch any errors and log it otherwise it remains hidden
            except Exception:  # pylint:disable=broad-except
                self.logger.exception("Error occured updating component state")

        # when the error events stop, tango emits a valid event for all
        # the error events we got for the various attribute subscriptions.
        # update the communication state in case the error event callback flipped it
        self.sync_communication_to_valid_event(attr_name)

    def _handle_error_event(self, event_data: tango.EventData) -> None:
        """Handle error events from attr subscription.

        :param event_data: data representing tango event
        :type event_data: tango.EventData
        """
        # Error events come through with attr_name being the full TRL so extract just the attribute
        # name to match what is added in _update_state_from_event
        attr_name = event_data.attr_name.split("/")[-1].lower()
        errors = event_data.errors

        self.logger.debug(
            (
                "Error event was emitted by device %s with the following details "
                "attr_name: %s, "
                "errors: %s"
            ),
            self._tango_device_fqdn,
            attr_name,
            errors,
        )

        # Tango error events are emitted for a number of reasons. Errors like `API_MissedEvents`
        # is tango's acknowledgement that something was dropped along the wire but doesn't mean
        # the heart beat has failed. For now, only heart beat failures on the event channel will
        # be further actioned after logging.
        dev_error = errors[0]
        if dev_error.reason == "API_EventTimeout":
            device_proxy = self._device_proxy_factory.get_cached_proxy(self._tango_device_fqdn)
            try:
                self._active_attr_event_subscriptions.remove(attr_name)
            except KeyError:
                pass

            if device_proxy is None:
                device_available = False
            else:
                try:
                    device_proxy.ping()
                except tango.DevFailed:
                    device_available = False
                else:
                    device_available = True

            if not device_available:
                self.logger.debug(
                    "Device at %s is unavailable. Communication status is being "
                    "set to NOT_ESTABLISHED.",
                    self._tango_device_fqdn,
                    extra=OPERATOR_TAG,
                )
                self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)

    def dispatch_event(self, event: type_hints.EventDataType) -> None:
        """Route a Tango event to the appropriate event handler.

        Only ``tango.EventData`` attribute events are supported. Other Tango event
        types are logged and ignored.

        Events marked as errors are handled by ``_handle_error_event()``, except
        when the attribute quality is ``ATTR_INVALID``. Invalid-quality attribute
        events are treated as state updates rather than communication failures.

        :param event: Tango event received from the callback scheduler.
        """
        if not isinstance(event, tango.EventData):
            self.logger.warning(
                "Ignoring unexpected event type %s received from device %s",
                type(event).__name__,
                self._tango_device_fqdn,
            )
            return

        # an invalid attribute event should not
        # be treated as a communication failure.
        error = event.err
        if (
            error
            and event.attr_value is not None
            and event.attr_value.quality == tango.AttrQuality.ATTR_INVALID
        ):
            error = False

        if error:
            self._handle_error_event(event)
        else:
            self._update_state_from_event(event)

    # --------------
    # helper methods
    # --------------

    def _fetch_build_state_information(self) -> None:
        if isinstance(self._tango_device_fqdn, tuple):
            self._tango_device_fqdn = self._tango_device_fqdn[0]
        build_state_attr = (
            "swVersions" if "spf" in self._tango_device_fqdn.lower() else "buildState"
        )
        try:
            build_state = self.read_attribute_value(build_state_attr)
        except tango.DevFailed:
            build_state = ""
        else:
            build_state = str(build_state)
        self._update_component_state(buildstate=build_state)

    def sync_communication_to_valid_event(self, event_attr_name: str) -> None:
        """Sync communication state with valid events from monitored attributes."""
        monitored_attrs = set(self._monitored_attributes)
        previous_subscriptions = set(self._active_attr_event_subscriptions)
        current_subscriptions = self._active_attr_event_subscriptions
        current_subscriptions.add(event_attr_name)

        if event_attr_name in monitored_attrs and len(current_subscriptions) > len(
            previous_subscriptions
        ):
            self.logger.info(
                "Attribute name [%s] is now valid, communication with [%s] is established",
                event_attr_name,
                self._tango_device_fqdn,
            )
            if self._communication_state != CommunicationStatus.ESTABLISHED:
                self._update_communication_state(CommunicationStatus.ESTABLISHED)
                self._fetch_build_state_information()

    def clear_monitored_attributes(self) -> None:
        """Sets all the monitored attribute values to 0.

        This is a helper method that can be called before
        update_state_from_monitored_attributes
        to ensure that dishManager's CM will update its attributes.

        DishManager will only update its attributes when a tango device CM
        pushes a change event, by setting all the monitored attributes to 0
        before calling update_state_from_monitored_attributes we can ensure that there will
        be a change and that dishManager will update its attributes.
        """
        for monitored_attribute in self._monitored_attributes:
            # Update it in the component state if it is there
            _monitored_attribute = monitored_attribute.lower()

            if _monitored_attribute in self._component_state:
                self._component_state[_monitored_attribute] = 0

    def update_state_from_monitored_attributes(
        self, monitored_attributes: Tuple[str, ...] | None = None
    ) -> None:
        """Update the component state by reading the monitored attributes.

        When an attribute on the device does not match the component_state
        it won't update unless it changes value (changes are updated via
        events).

        This is a convenience method that can be called to sync up the
        monitored attributes on the device and the component state.
        """
        device_proxy = self._device_proxy_factory(self._tango_device_fqdn)

        # fallback to defaults if not provided
        monitored_attributes = monitored_attributes or self._monitored_attributes

        with tango.EnsureOmniThread():
            try:
                attribute_values = device_proxy.read_attributes(monitored_attributes)
            except tango.DevFailed:
                self.logger.error(
                    "Encountered an error retrieving the current values of %s from %s",
                    monitored_attributes,
                    self._tango_device_fqdn,
                )
                return

        monitored_attribute_values = {}
        for attr_value in attribute_values:
            attr_name = attr_value.name.lower()
            value = attr_value.value
            if isinstance(value, np.ndarray):
                value = list(value)
            monitored_attribute_values[attr_name] = value

        self._update_component_state(**monitored_attribute_values)

    def _interpret_command_reply(self, command_name: str, reply: Any) -> Tuple[TaskStatus, Any]:
        """Default interpretation: return IN_PROGRESS and the reply."""
        reply = reply or f"{command_name} successfully executed"
        return TaskStatus.IN_PROGRESS, reply

    @check_communicating
    def execute_command(self, command_name: str, command_arg: Any) -> Tuple[TaskStatus, Any]:
        """Check the connection and execute the command on the Tango device."""
        self.logger.debug(
            "About to execute command [%s] on device [%s] with param [%s]",
            command_name,
            self._tango_device_fqdn,
            command_arg,
        )
        reply = None
        device_proxy = self._device_proxy_factory(self._tango_device_fqdn)

        with tango.EnsureOmniThread():
            try:
                reply = device_proxy.command_inout(command_name, command_arg)
            except tango.DevFailed as err:
                err_description = "".join([str(arg.desc) for arg in err.args])
                self.logger.error(
                    "Encountered an error executing [%s] with arg [%s] on [%s]: %s",
                    command_name,
                    command_arg,
                    self._tango_device_fqdn,
                    err_description,
                )
                return TaskStatus.FAILED, err_description

        if not isinstance(reply, (list, tuple)):
            reply = reply or f"{command_name} successfully executed"
            return TaskStatus.IN_PROGRESS, reply
        return self._interpret_command_reply(command_name, reply)

    @check_communicating
    def read_attribute_value(self, attribute_name: str, log_read: bool = True) -> Any:
        """Check the connection and read an attribute."""
        if log_read:
            self.logger.debug(
                "About to read attribute [%s] on device [%s]",
                attribute_name,
                self._tango_device_fqdn,
            )
        device_proxy = self._device_proxy_factory(self._tango_device_fqdn)
        with tango.EnsureOmniThread():
            try:
                result = device_proxy.read_attribute(attribute_name).value
            except tango.DevFailed:
                self.logger.exception(
                    "Could not read attribute [%s] on [%s]",
                    attribute_name,
                    self._tango_device_fqdn,
                )
                raise
            if log_read:
                self.logger.debug(
                    "Result of reading [%s] on [%s] is [%s]",
                    attribute_name,
                    self._tango_device_fqdn,
                    result,
                )
            return result

    @check_communicating
    def write_attribute_value(self, attribute_name: str, attribute_value: Any) -> None:
        """Check the connection and write an attribute."""
        self.logger.debug(
            "About to write attribute [%s] on device [%s]",
            attribute_name,
            self._tango_device_fqdn,
        )
        device_proxy = self._device_proxy_factory(self._tango_device_fqdn)
        with tango.EnsureOmniThread():
            result = None
            try:
                result = device_proxy.write_attribute(attribute_name, attribute_value)
            except tango.DevFailed:
                self.logger.exception(
                    "Could not write to attribute [%s] with [%s] on [%s]",
                    attribute_name,
                    attribute_value,
                    self._tango_device_fqdn,
                )
                raise
            self.logger.debug(
                "Result of writing [%s] on [%s] is [%s]",
                attribute_name,
                self._tango_device_fqdn,
                result,
            )
            return result

    def _initialize_events_monitor(self) -> None:
        """Initialize the events monitor and queue."""
        # NOTE:
        # Keep thread_count=1 so that Tango events, component-state updates, and
        # communication-state transitions are processed sequentially. This preserves
        # the behaviour of the original TangoDeviceComponentManager and avoids
        # concurrent access to shared component-manager state.
        #
        # Increasing thread_count would allow callbacks from different event streams
        # to execute concurrently, which may improve responsiveness for high-rate
        # attributes. However, this would require all shared state, including
        # component-state updates and subscription management, to be fully
        # thread-safe.
        #
        # TODO: Evaluate increasing thread_count and allocating a dedicated queue for
        # high-rate attributes (e.g. achievedPointing) if event-processing latency
        # becomes an issue.
        self._events_monitor = CallbackScheduler(
            thread_count=1, logger=self.logger, name="events_monitor"
        )

        shared_events_queue = self._events_monitor.allocate_queue(queue_size=32)

        def queue_factory() -> Queue:
            return shared_events_queue

        # set up change events subscriptions for all monitored attributes
        for attr in self._monitored_attributes:
            self._events_monitor.register_event_callback(
                self._tango_device_fqdn,
                attr,
                tango.EventType.CHANGE_EVENT,
                self.dispatch_event,
                queue_factory=queue_factory,
            )

    def _start_monitoring_when_proxy_available(self) -> None:
        """Create and cache the device proxy, then start event monitoring.

        Proxy creation and connection retries run on this dedicated thread so that
        ``start_communicating()`` remains non-blocking. Event subscriptions are
        registered only after the proxy has been cached successfully.
        """
        self.logger.info(
            "Waiting for device %s to become available.",
            self._tango_device_fqdn,
        )

        while not self._dp_factory_signal.is_set():
            try:
                self._device_proxy_factory(self._tango_device_fqdn)
            except RuntimeError:
                # DeviceProxyManager raises RuntimeError when communication is stopped
                # (e.g. stop_communicating) while a connection attempt is in progress.
                return
            except tango.DevFailed:
                self.logger.debug(
                    "Unable to connect to device %s; retrying.",
                    self._tango_device_fqdn,
                )
                continue

            # just in case the signal was set while the proxy was being
            # created check it again before starting event monitoring
            if self._dp_factory_signal.is_set():
                return

            if self._events_monitor is None:
                self._initialize_events_monitor()

            return

    def _start_event_monitoring(self) -> None:
        """Start the events monitor and begin processing events."""
        # e.g. mid-dish/simulator-spfc/SKA001 -> mid_dish.simulator_spfc.SKA001
        thread_name = self._tango_device_fqdn.replace("/", ".").replace("-", "_")
        self._connection_thread = Thread(
            target=self._start_monitoring_when_proxy_available,
            name=f"{thread_name}.connection_thread",
            daemon=True,
        )
        self._connection_thread.start()

    def _stop_event_monitoring(self) -> None:
        """Shut down the events monitor and clear subscription tracking."""
        if self._events_monitor is not None:
            self._events_monitor.shutdown()

        self._events_monitor = None
        self._active_attr_event_subscriptions.clear()

    def start_communicating(self) -> None:
        """Establish communication with the device."""
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
        self.logger.info(
            f"Establishing communication with {self._tango_device_fqdn}.", extra=OPERATOR_TAG
        )

        if self._events_monitor is not None:
            self.logger.debug(
                "Event monitoring for %s is already active.",
                self._tango_device_fqdn,
            )
            return

        if self._connection_thread is not None and self._connection_thread.is_alive():
            self.logger.debug(
                "Connection to %s is already being established.",
                self._tango_device_fqdn,
            )
            return

        self._dp_factory_signal.clear()
        self._start_event_monitoring()

    def stop_communicating(self) -> None:
        """Stop communication with the device."""
        self.logger.info(
            f"Stopping communication with {self._tango_device_fqdn}.", extra=OPERATOR_TAG
        )
        self._dp_factory_signal.set()

        if self._connection_thread is not None and self._connection_thread.is_alive():
            self._connection_thread.join()
            self._connection_thread = None

        self._stop_event_monitoring()
        self._device_proxy_factory.factory_reset()
        self._update_communication_state(CommunicationStatus.DISABLED)
