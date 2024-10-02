"""Generic component manager for a subservient tango device"""

import logging
import typing
import uuid
from queue import Empty, Queue
from threading import Event, Thread
from typing import Any, Callable, Optional, Tuple

import numpy as np
import tango
from ska_control_model import CommunicationStatus, ResultCode, TaskStatus
from ska_tango_base.executor import TaskExecutorComponentManager
from ska_tango_base.faults import CommandError, ResultCodeError
from ska_tango_base.long_running_commands_api import invoke_lrc

from ska_mid_dish_manager.component_managers.device_monitor import TangoDeviceMonitor


def _check_connection(func: Any) -> Any:  # pylint: disable=E0213
    """Connection check decorator.

    This is a workaround for decorators in classes.

    Execute the method, if communication fails, commence reconnection.
    """

    def _decorator(self, *args: Any, **kwargs: Any) -> Callable:  # type: ignore
        if self.communication_state != CommunicationStatus.ESTABLISHED:
            raise LostConnection("Communication status not ESTABLISHED")
        return func(self, *args, **kwargs)  # pylint: disable=E1102

    return _decorator


class LostConnection(Exception):
    """Exception for losing connection to the Tango device"""


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
        self._component_state: dict = {}  # type: ignore
        self._communication_state_callback = communication_state_callback
        self._component_state_callback = component_state_callback
        self._quality_state_callback = quality_state_callback
        self._events_queue: Queue = Queue()
        self._tango_device_fqdn = tango_device_fqdn
        self._monitored_attributes = monitored_attributes
        self._quality_monitored_attributes = quality_monitored_attributes
        if not logger:
            logger = logging.getLogger()
        self.logger = logger

        self._tango_device_monitor = TangoDeviceMonitor(
            self._tango_device_fqdn,
            self._monitored_attributes,
            self._events_queue,
            logger,
            self._update_communication_state,
        )

        self._event_consumer_thread: Optional[Thread] = None
        self._event_consumer_abort_event: Optional[Event] = None

        super().__init__(
            logger,
            *args,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            **kwargs,
        )

        self._update_communication_state(communication_state=CommunicationStatus.NOT_ESTABLISHED)

        # Default to NOT_ESTABLISHED
        if self._communication_state_callback:
            self._communication_state_callback()  # type: ignore

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
        """Update the component state by reading the monitored attributes

        When an attribute on the device does not match the component_state
        it won't update unless it changes value (changes are updated via
        events).

        This is a convenience method that can be called to sync up the
        monitored attributes on the device and the component state.
        """
        with tango.EnsureOmniThread():
            device_proxy = tango.DeviceProxy(self._tango_device_fqdn)
            monitored_attribute_values = {}
            for monitored_attribute in self._monitored_attributes:
                monitored_attribute = monitored_attribute.lower()

                # Add it to component state if not there
                if monitored_attribute not in self._component_state:
                    self._component_state[monitored_attribute] = None

                value = device_proxy.read_attribute(monitored_attribute).value
                if isinstance(value, np.ndarray):
                    value = list(value)
                monitored_attribute_values[monitored_attribute] = value
            self._update_component_state(**monitored_attribute_values)

    def _update_state_from_event(self, event_data: tango.EventData) -> None:
        """Update component state as the change events come in.

        :param event_data: Tango event
        :type event_data: tango.EventData
        """
        # I get lowercase and uppercase "State" from events
        # for some reason, stick to lowercase to avoid duplicates
        attr_name = event_data.attr_value.name.lower()

        # Add it to component state if not there
        if attr_name not in self._component_state:
            self._component_state[attr_name] = None

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
                self.logger.exception("Error updating component state")

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
                self._event_consumer_cb,
            ],
        )
        self._event_consumer_thread.start()

    # pylint: disable=too-many-arguments
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

    def _event_consumer_cb(self, event_data: tango.EventData) -> None:
        """Just log the error event

        :param event_data: data representing tango event
        :type event_data: tango.EventData
        """
        attr_name = event_data.attr_name
        received_timestamp = event_data.reception_date.totime()
        event_type = event_data.event
        value = event_data.attr_value
        errors = event_data.errors
        # Events with errors do not send the attribute value
        # so regard its reading as invalid.
        quality = tango.AttrQuality.ATTR_INVALID

        self.logger.debug(
            (
                "Error event was emitted by device [%s] with the following details: "
                "attr_name: %s"
                "received_timestamp: %s"
                "event_type: %s"
                "value: %s"
                "quality: %s"
                "errors: %s"
            ),
            self._tango_device_fqdn,
            attr_name,
            received_timestamp,
            event_type,
            value,
            quality,
            errors,
        )

        if self.communication_state == CommunicationStatus.ESTABLISHED:
            self.logger.info("Reconnecting to %s", self._tango_device_fqdn)
            self._tango_device_monitor.monitor()

    def run_device_command(
        self, command_name: str, command_arg: Any, task_callback: Callable = None  # type: ignore
    ) -> Any:
        """Execute the command in a thread"""
        task_status, response = self.submit_task(
            self.invoke_device_command,
            args=[command_name, command_arg],
            task_callback=task_callback,
        )
        return task_status, response

    # pylint: disable=unnecessary-pass
    def lrc_callback(self, status=None, **kwargs) -> None:
        """Callback to be passed to invoke_lrc, updating LRC status value."""
        pass

    @typing.no_type_check
    def invoke_device_command(
        self,
        command_name: str,
        command_arg: Any,
        task_callback: Callable = None,
        task_abort_event: Event = None,
    ) -> None:
        """Function to execute command on subdevice."""
        if task_abort_event and task_abort_event.is_set():
            task_callback(status=TaskStatus.ABORTED)
            return

        cmd_response = None

        if "ds" in self._tango_device_fqdn:
            try:
                cmd_response = self.wrap_invoke_lrc(command_name, command_arg)
            except (CommandError, ResultCodeError, tango.DevFailed) as err:
                if task_callback:
                    task_callback(status=TaskStatus.FAILED, exception=(ResultCode.FAILED, err))
                return
        else:
            try:
                cmd_response = self.execute_command(command_name, command_arg)
            except (LostConnection, tango.DevFailed) as err:
                if task_callback:
                    task_callback(status=TaskStatus.FAILED, exception=(ResultCode.FAILED, err))
                return

            # this is not entirely true. we just dont know what attribute
            # to watch on the device to determine the command finished, so
            # reporting completed for now and marking a TODO to re-use invoke_lrc
            if task_callback:
                task_callback(status=TaskStatus.COMPLETED)

        self.logger.debug(
            "Result of [%s] on [%s] is [%s]",
            command_name,
            self._tango_device_fqdn,
            cmd_response,
        )

    @_check_connection
    def wrap_invoke_lrc(self, cmd_name, cmd_arg) -> Any:
        """Invokes LRC execution on subdevices."""
        with tango.EnsureOmniThread():
            device_proxy = tango.DeviceProxy(self._tango_device_fqdn)
        try:
            lrc_subscriptions = invoke_lrc(self.lrc_callback, device_proxy, cmd_name, (cmd_arg,))
        except CommandError:
            self.logger.exception(
                "Device [%s] rejected command [%s]",
                self._tango_device_fqdn,
                cmd_name,
            )
            raise
        except ResultCodeError:
            self.logger.exception(
                "Device [%s] returned unexpected result code",
                self._tango_device_fqdn,
            )
            raise
        except tango.DevFailed:
            self.logger.exception(
                "Command call [%s] failed on device [%s]",
                cmd_name,
                self._tango_device_fqdn,
            )
            raise
        return lrc_subscriptions.command_id

    @_check_connection
    def execute_command(self, command_name: str, command_arg: Any) -> Any:
        """Check the connection and execute the command on the Tango device"""
        self.logger.debug(
            "About to execute command [%s] on device [%s] with param [%s]",
            command_name,
            self._tango_device_fqdn,
            command_arg,
        )
        response = None
        with tango.EnsureOmniThread():
            device_proxy = tango.DeviceProxy(self._tango_device_fqdn)
            try:
                response = device_proxy.command_inout(command_name, command_arg)
            except tango.DevFailed:
                self.logger.exception(
                    "Could not execute command [%s] with arg [%s] on [%s]",
                    command_name,
                    command_arg,
                    self._tango_device_fqdn,
                )
                raise
        # generate a pseudo unique_id for commands
        # that go through and return nothing. this
        # is for the dish lmc tango devie simulators
        if response is None:
            response = f"{self._tango_device_fqdn}_{uuid.uuid1()}"
        return response

    @_check_connection
    def read_attribute_value(self, attribute_name: str) -> Any:
        """Check the connection and read an attribute"""
        self.logger.debug(
            "About to read attribute [%s] on device [%s]",
            attribute_name,
            self._tango_device_fqdn,
        )
        with tango.EnsureOmniThread():
            device_proxy = tango.DeviceProxy(self._tango_device_fqdn)
            result = getattr(device_proxy, attribute_name)
            self.logger.debug(
                "Result of reading [%s] on [%s] is [%s]",
                attribute_name,
                self._tango_device_fqdn,
                result,
            )
            return result

    @_check_connection
    def write_attribute_value(self, attribute_name: str, attribute_value: Any) -> None:
        """Check the connection and write an attribute"""
        self.logger.debug(
            "About to write attribute [%s] on device [%s]",
            attribute_name,
            self._tango_device_fqdn,
        )

        # Note: If this function is called at a high rate then re-creating the device proxy
        # here will be inefficient. Consider moving the declaration out of this function.
        with tango.EnsureOmniThread():
            device_proxy = tango.DeviceProxy(self._tango_device_fqdn)
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
        # pylint: disable=no-member
        self.logger.info("start_communicating")
        self._tango_device_monitor.monitor()
        self._start_event_consumer_thread()

    def stop_communicating(self) -> None:
        """Stop communication with the device"""
        # pylint: disable=no-member
        self._tango_device_monitor.stop_monitoring()
        self._stop_event_consumer_thread()
