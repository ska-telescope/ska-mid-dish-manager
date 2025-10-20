"""Generic component manager for a subservient tango device."""

import logging
from queue import Empty, Queue
from threading import Event, Thread
from typing import Any, Callable, Optional, Tuple

import numpy as np
import tango
from ska_control_model import CommunicationStatus, TaskStatus
from ska_tango_base.base import BaseComponentManager

from ska_mid_dish_manager.component_managers.device_monitor import TangoDeviceMonitor
from ska_mid_dish_manager.component_managers.device_proxy_factory import DeviceProxyManager
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
        self._events_queue: Queue = Queue()
        self._tango_device_fqdn = tango_device_fqdn
        self._monitored_attributes = tuple(attr.lower() for attr in monitored_attributes)
        self._quality_monitored_attributes = tuple(
            attr.lower() for attr in quality_monitored_attributes
        )
        self._active_attr_event_subscriptions: set[str] = set()
        self.logger = logger
        self._dp_factory_signal: Event = Event()
        self._event_consumer_thread: Optional[Thread] = None
        self._event_consumer_abort_event: Optional[Event] = None

        self._device_proxy_factory = DeviceProxyManager(self.logger, self._dp_factory_signal)
        self._tango_device_monitor = TangoDeviceMonitor(
            self._tango_device_fqdn,
            self._device_proxy_factory,
            self._monitored_attributes,
            self._events_queue,
            logger,
        )

        # make sure everything monitored is in the component state
        attr_names_lower = map(lambda x: x.lower(), monitored_attributes)
        attrs_to_be_added = set(attr_names_lower).difference(kwargs.keys())
        kwargs.update(dict.fromkeys(attrs_to_be_added))

        super().__init__(
            logger,
            *args,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            buildstate="",  # this needed for buildState refresh
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

    def _handle_error_events(self, event_data: tango.EventData) -> None:
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
            try:
                self._active_attr_event_subscriptions.remove(attr_name)
            except KeyError:
                pass

            self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)

    # --------------
    # helper methods
    # --------------

    def _fetch_build_state_information(self) -> None:
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
        previously_synced = monitored_attrs == self._active_attr_event_subscriptions
        self._active_attr_event_subscriptions.add(event_attr_name)
        currently_synced = monitored_attrs == self._active_attr_event_subscriptions

        if not previously_synced and currently_synced:
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

        # TODO ST 10-2025 Passing monitored_attributes doesn't work for configureband command
        # because it only checks that configuredBand is B[x] but dishMode is also needed
        # cross checks all the other commands or just wait for feature branch with new S&M
        # fallback to defaults if not provided
        # monitored_attributes = monitored_attributes or self._monitored_attributes
        monitored_attributes = self._monitored_attributes

        with tango.EnsureOmniThread():
            monitored_attribute_values = {}
            for monitored_attribute in monitored_attributes:
                attr = monitored_attribute.lower()
                try:
                    value = device_proxy.read_attribute(attr).value
                except tango.DevFailed:
                    self.logger.error(
                        "Encountered an error retrieving the current value of %s from %s",
                        attr,
                        self._tango_device_fqdn,
                    )
                    continue

                if isinstance(value, np.ndarray):
                    value = list(value)

                monitored_attribute_values[attr] = value

            self._update_component_state(**monitored_attribute_values)

    @classmethod
    def _event_consumer(
        cls,
        event_queue: Queue,
        valid_event_cb: Callable,
        task_abort_event: Optional[Event] = None,
        error_event_cb: Optional[Callable] = None,  # type: ignore
    ) -> None:
        while task_abort_event and not task_abort_event.is_set():
            try:
                event_data = event_queue.get(timeout=1)
                error = event_data.err
                # If a tango error has been flagged, due to an invalid attribute, do not
                # interpret it as communication error.
                if error and event_data.attr_value:
                    if event_data.attr_value.quality == tango.AttrQuality.ATTR_INVALID:
                        error = False

                if error:
                    if error_event_cb:
                        error_event_cb(event_data)
                    continue
                valid_event_cb(event_data)
            except Empty:
                pass

    def _stop_event_consumer_thread(self) -> None:
        """Stop the event consumer thread if it is alive."""
        if (
            self._event_consumer_thread is not None
            and self._event_consumer_abort_event is not None
            and self._event_consumer_thread.is_alive()
        ):
            self._event_consumer_abort_event.set()
            self._event_consumer_thread.join()

    def _start_event_consumer_thread(self) -> None:
        """Start the event consumer thread.

        This method is idempotent. When called the existing (if any)
        event consumer thread is removed and recreated.
        """
        self._stop_event_consumer_thread()

        self._event_consumer_abort_event = Event()
        self._event_consumer_thread = Thread(
            target=self._event_consumer,
            args=[
                self._events_queue,
                self._update_state_from_event,
                self._event_consumer_abort_event,
                self._handle_error_events,
            ],
        )

        # e.g. mid-dish/simulator-spfc/SKA001 -> mid_dish.simulator_spfc.SKA001
        formatted_fqdn = self._tango_device_fqdn.replace("/", ".").replace("-", "_")
        self._event_consumer_thread.name = f"{formatted_fqdn}.event_consumer_thread"
        self._event_consumer_thread.start()

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
    def read_attribute_value(self, attribute_name: str) -> Any:
        """Check the connection and read an attribute."""
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

    def start_communicating(self) -> None:
        """Establish communication with the device."""
        self.logger.info(f"Establish communication with {self._tango_device_fqdn}")
        self._dp_factory_signal.clear()
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
        self._tango_device_monitor.monitor()
        self._start_event_consumer_thread()

    def stop_communicating(self) -> None:
        """Stop communication with the device."""
        self.logger.info(f"Stop communication with {self._tango_device_fqdn}")
        self._dp_factory_signal.set()
        self._tango_device_monitor.stop_monitoring()
        self._active_attr_event_subscriptions.clear()
        self._stop_event_consumer_thread()
        self._events_queue.queue.clear()
        self._update_communication_state(CommunicationStatus.DISABLED)
