"""Generic component manager for a subservient tango device"""
import datetime
import logging
import typing
from queue import Empty, PriorityQueue
from threading import Event
from typing import Any, Callable, Optional, Tuple

import numpy as np
import tango
from ska_control_model import CommunicationStatus, ResultCode, TaskStatus
from ska_tango_base.executor import TaskExecutorComponentManager

from ska_mid_dish_manager.component_managers.device_monitor import TangoDeviceMonitor
from ska_mid_dish_manager.models.dish_mode_model import PrioritizedEventData


def _check_connection(func: Any) -> Any:  # pylint: disable=E0213
    """Connection check decorator.

    This is a workaround for decorators in classes.

    Execute the method, if communication fails, commence reconnection.
    """

    def _decorator(self: TangoDeviceComponentManager, *args: Any, **kwargs: Any) -> Callable:
        if self.communication_state != CommunicationStatus.ESTABLISHED:
            raise LostConnection("Communication status not ESTABLISHED")
        return func(self, *args, **kwargs)  # pylint: disable=E1102

    return _decorator


class LostConnection(Exception):
    """Exception for losing connection to the Tango device"""


# pylint: disable=abstract-method, too-many-instance-attributes, no-member
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
        **kwargs: Any,
    ):
        self._component_state = {}
        self._communication_state_callback = communication_state_callback
        self._component_state_callback = component_state_callback
        self._events_queue: PriorityQueue = PriorityQueue()
        self._tango_device_fqdn = tango_device_fqdn
        self._monitored_attributes = monitored_attributes
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

        super().__init__(
            logger,
            *args,
            max_workers=20,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            **kwargs,
        )

        self._update_communication_state(communication_state=CommunicationStatus.NOT_ESTABLISHED)

        # Default to NOT_ESTABLISHED
        if self._communication_state_callback:
            self._communication_state_callback() # type: ignore
        self._start_event_consumer_thread()

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
        device_proxy = tango.DeviceProxy(self._tango_device_fqdn)
        for monitored_attribute in self._monitored_attributes:
            # Add it to component state if not there
            if monitored_attribute not in self._component_state:
                self._component_state[monitored_attribute] = None

            value = device_proxy.read_attribute(monitored_attribute).value
            if isinstance(value, np.ndarray):
                value = list(value)
            self._update_component_state(**{monitored_attribute: value})

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

        try:
            value = event_data.attr_value.value
            if isinstance(value, np.ndarray):
                value = list(value)
            self._update_component_state(**{attr_name: value})
        # Catch any errors and log it otherwise it remains hidden
        except Exception:  # pylint:disable=broad-except
            self.logger.exception("Error updating component state")

    def _start_event_consumer_thread(self) -> None:
        self.submit_task(
            self._event_consumer,
            args=[
                self._events_queue,
                self._update_state_from_event,
            ],
            task_callback=self._event_consumer_cb,
        )

    # pylint: disable=too-many-arguments
    @classmethod
    def _event_consumer(
        cls,
        event_queue: PriorityQueue,
        update_state_cb: Callable,
        task_abort_event: Optional[Event] = None,
        task_callback: Optional[Callable] = None,  # type: ignore
    ) -> None:
        if task_callback:
            task_callback(status=TaskStatus.IN_PROGRESS)
        latest_valid_event_timestamp = datetime.datetime.now() - datetime.timedelta(hours=1)
        while task_abort_event and not task_abort_event.is_set():
            try:
                p_event_data: PrioritizedEventData = event_queue.get(timeout=1)
                event_data = p_event_data.item
                if event_data.err:
                    # If we get an error event that is older than the latest valid event
                    # then discard it. If it's a new error event then start the reconnection
                    # process via task_callback and drain until we find a valid event
                    if event_data.reception_date.todatetime() > latest_valid_event_timestamp:
                        # Restart the connection
                        if task_callback:
                            task_callback(progress="Error Event Found")
                        # Drain the remaining errors
                        while event_data.err:
                            p_event_data = event_queue.get(timeout=1)
                            event_data = p_event_data.item

                if event_data.attr_value:
                    latest_valid_event_timestamp = event_data.reception_date.todatetime()
                    update_state_cb(event_data)
            except Empty:
                pass
        if task_callback:
            task_callback(status=TaskStatus.ABORTED)

    def _event_consumer_cb(
        self,
        status: Optional[TaskStatus] = None,
        progress: Optional[int] = None,
        result: Optional[tuple[ResultCode, str]] = None,
        exception: Optional[Exception] = None,
    ) -> None:
        """Just log the status of the event handler thread

        :param status: _description_, defaults to None
        :type status: Optional[TaskStatus], optional
        :param progress: _description_, defaults to None
        :type progress: Optional[int], optional
        :param result: _description_, defaults to None
        :type result: Optional[tuple[ResultCode, str]], optional
        :param exception: _description_, defaults to None
        :type exception: Optional[Exception], optional
        """
        self.logger.debug(
            (
                "Device [%s] event handler callback status [%s], "
                "progress [%s] result [%s], exception [%s]"
            ),
            self._tango_device_fqdn,
            status,
            progress,
            result,
            exception,
        )
        if progress and progress == "Error Event Found":
            self.logger.info("Reconnecting to %s", self._tango_device_fqdn)
            if self.communication_state == CommunicationStatus.ESTABLISHED:
                self._tango_device_monitor.monitor()

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
        except (LostConnection, tango.DevFailed) as err:
            self.logger.exception(err)
            if task_callback:
                task_callback(status=TaskStatus.FAILED, exception=err)
            return

        # perform another abort event check in case it was missed earlier
        if task_abort_event.is_set():
            task_callback(progress=f"{command_name} was aborted")

        if task_callback:
            task_callback(status=TaskStatus.COMPLETED, result=str(result))

    @_check_connection
    def execute_command(self, command_name: str, command_arg: Any) -> Any:
        """Check the connection and execute the command on the Tango device"""
        self.logger.debug(
            "About to execute command [%s] on device [%s]",
            command_name,
            self._tango_device_fqdn,
        )
        device_proxy = tango.DeviceProxy(self._tango_device_fqdn)
        result = device_proxy.command_inout(command_name, command_arg)
        self.logger.debug(
            "Result of [%s] on [%s] is [%s]",
            command_name,
            self._tango_device_fqdn,
            result,
        )
        return result

    @_check_connection
    def read_attribute_value(self, attribute_name: str) -> Any:
        """Check the connection and read an attribute"""
        self.logger.debug(
            "About to read attribute [%s] on device [%s]",
            attribute_name,
            self._tango_device_fqdn,
        )
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
        """Check the connection and read an attribute"""
        self.logger.debug(
            "About to write attribute [%s] on device [%s]",
            attribute_name,
            self._tango_device_fqdn,
        )
        device_proxy = tango.DeviceProxy(self._tango_device_fqdn)
        result = device_proxy.write_attribute(attribute_name, attribute_value)
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

    def stop_communicating(self) -> None:
        """Stop communication with the device"""
        # pylint: disable=no-member
        self._tango_device_monitor.stop_monitoring()
