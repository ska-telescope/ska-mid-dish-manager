"""Generic component manager for a subservient tango device"""

import logging
import typing
from queue import Empty, Queue
from threading import Event, Thread
from typing import Any, Callable, Optional, Tuple

import numpy as np
import tango
from ska_control_model import CommunicationStatus, ResultCode, TaskStatus
from ska_tango_base.executor import TaskExecutorComponentManager

from ska_mid_dish_manager.component_managers.device_monitor import TangoDeviceMonitor
from ska_mid_dish_manager.component_managers.device_proxy_factory import DeviceProxyManager
from ska_mid_dish_manager.utils.decorators import check_communicating


# pylint: disable=abstract-method, too-many-instance-attributes, no-member, too-many-arguments
class TangoDeviceComponentManager(TaskExecutorComponentManager):
    """A component manager for a Tango device"""

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
        self._communication_state_callback = communication_state_callback
        self._component_state_callback = component_state_callback
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
            self._sync_communication_to_subscription,
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
            **kwargs,
        )

    # ---------
    # Callbacks
    # ---------

    def _sync_communication_to_subscription(self, subscribed_attrs: list[str]) -> None:
        """
        Reflect status of monitored attribute subscription on communication state

        :param subscribed_attrs: the attributes with successful change event subscription
        :type subscribed_attrs: list
        """
        # save a copy of the subscribed attributes. this will be
        # evaluated by the function processing the valid events
        self._active_attr_event_subscriptions = set(subscribed_attrs)
        all_subscribed = set(self._monitored_attributes) == set(subscribed_attrs)
        if all_subscribed:
            self._update_communication_state(CommunicationStatus.ESTABLISHED)
            # send over the build state after all attributes are subscribed
            self._fetch_build_state_information()
        else:
            self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
            self.logger.debug("SPFRX_TEST: Monitored [%s].", set(self._monitored_attributes))
            self.logger.debug("SPFRX_TEST: subscribed [%s].", set(subscribed_attrs))

    def _update_state_from_event(self, event_data: tango.EventData) -> None:
        """
        Update component state as the change events come in.

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

        # if the error event stops, tango emits a valid event for all
        # the error events we got for the various attribute subscriptions.
        # update the communication state in case the error event callback flipped it
        self._active_attr_event_subscriptions.add(attr_name)
        self.sync_communication_to_valid_event(attr_name)

    def _handle_error_events(self, event_data: tango.EventData) -> None:
        """
        Handle error events from attr subscription

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

    def sync_communication_to_valid_event(self, attr_name) -> None:
        """Sync communication state with valid events from monitored attributes"""
        all_monitored_events_valid = (
            set(self._monitored_attributes) == self._active_attr_event_subscriptions
        )
        self.logger.debug("SPFRX_TEST: Comm status [%s].", self.communication_state)
        self.logger.debug("SPFRX_TEST: Attribute [%s] received.", attr_name)
        self.logger.debug("SPFRX_TEST: Active sub [%s].", self._active_attr_event_subscriptions)
        self.logger.debug("SPFRX_TEST: Monitored sub [%s].", set(self._monitored_attributes))
        if all_monitored_events_valid:
            self._update_communication_state(CommunicationStatus.ESTABLISHED)

    def clear_monitored_attributes(self) -> None:
        """
        Sets all the monitored attribute values to 0.

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
            monitored_attribute = monitored_attribute.lower()

            if monitored_attribute in self._component_state:
                self._component_state[monitored_attribute] = 0

    def update_state_from_monitored_attributes(self) -> None:
        """
        Update the component state by reading the monitored attributes

        When an attribute on the device does not match the component_state
        it won't update unless it changes value (changes are updated via
        events).

        This is a convenience method that can be called to sync up the
        monitored attributes on the device and the component state.
        """
        device_proxy = self._device_proxy_factory(self._tango_device_fqdn)
        with tango.EnsureOmniThread():
            monitored_attribute_values = {}
            for monitored_attribute in self._monitored_attributes:
                monitored_attribute = monitored_attribute.lower()

                try:
                    value = device_proxy.read_attribute(monitored_attribute).value
                except tango.DevFailed:
                    self.logger.exception(
                        "Encountered an error retrieving the current value of %s from %s",
                        monitored_attribute,
                        self._tango_device_fqdn,
                    )
                    continue
                if isinstance(value, np.ndarray):
                    value = list(value)
                monitored_attribute_values[monitored_attribute] = value
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
                if event_data.err:
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
        """
        Start the event consumer thread.

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

        self._event_consumer_thread.name = f"{self._tango_device_fqdn}_event_consumer_thread"
        self._event_consumer_thread.start()

    def run_device_command(
        self, command_name: str, command_arg: Any, task_callback: Callable = None  # type: ignore
    ) -> Any:
        """Execute the command in a thread"""
        task_status, response = self.submit_task(
            self._run_device_command,
            args=[command_name, command_arg],
            task_callback=task_callback,
        )
        return task_status, response

    @typing.no_type_check
    def _run_device_command(
        self,
        command_name: str,
        command_arg: Any,
        task_callback: Callable = None,
        task_abort_event: Event = None,
    ) -> None:
        if task_abort_event.is_set():
            task_callback(status=TaskStatus.ABORTED)
            return

        if task_callback:
            task_callback(status=TaskStatus.IN_PROGRESS)

        result = None
        try:
            result = self.execute_command(command_name, command_arg)
        except tango.DevFailed as err:
            self.logger.exception(err)
            if task_callback:
                task_callback(status=TaskStatus.FAILED, exception=(ResultCode.FAILED, err))
            return

        # perform another abort event check in case it was missed earlier
        if task_abort_event.is_set():
            task_callback(progress=f"{command_name} was aborted")

        if task_callback:
            task_callback(status=TaskStatus.COMPLETED, result=(ResultCode.OK, str(result)))

    @check_communicating
    def execute_command(self, command_name: str, command_arg: Any) -> Any:
        """Check the connection and execute the command on the Tango device"""
        self.logger.debug(
            "About to execute command [%s] on device [%s] with param [%s]",
            command_name,
            self._tango_device_fqdn,
            command_arg,
        )
        result = None
        device_proxy = self._device_proxy_factory(self._tango_device_fqdn)
        with tango.EnsureOmniThread():
            try:
                result = device_proxy.command_inout(command_name, command_arg)
            except tango.DevFailed:
                self.logger.exception(
                    "Could not execute command [%s] with arg [%s] on [%s]",
                    command_name,
                    command_arg,
                    self._tango_device_fqdn,
                )
                raise
            self.logger.debug(
                "Result of [%s] on [%s] is [%s]",
                command_name,
                self._tango_device_fqdn,
                result,
            )
        return result

    @check_communicating
    def read_attribute_value(self, attribute_name: str) -> Any:
        """Check the connection and read an attribute"""
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
        """Check the connection and write an attribute"""
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

    @typing.no_type_check
    def start_communicating(self) -> None:
        """Establish communication with the device"""
        self.logger.info(f"Establish communication with {self._tango_device_fqdn}")
        self._dp_factory_signal.clear()
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
        self._tango_device_monitor.monitor()
        self._start_event_consumer_thread()

    def stop_communicating(self) -> None:
        """Stop communication with the device"""
        self.logger.info(f"Stop communication with {self._tango_device_fqdn}")
        self._dp_factory_signal.set()
        self._tango_device_monitor.stop_monitoring()
        self._stop_event_consumer_thread()
        self._update_communication_state(CommunicationStatus.DISABLED)
