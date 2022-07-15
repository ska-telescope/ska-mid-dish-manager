# pylint: disable=W0223
"""Component Manager for a Tango device"""
import time
from dataclasses import dataclass
from datetime import datetime
from threading import Event
from typing import Any, AnyStr, Callable, List, Optional

import tango
from ska_tango_base.base.component_manager import TaskExecutorComponentManager
from ska_tango_base.control_model import CommunicationStatus
from ska_tango_base.executor import TaskStatus

SLEEP_TIME_BETWEEN_RECONNECTS = 1  # seconds
STATE_ATTR_POLL_PERIOD = 3000


class LostConnection(Exception):
    """Exception for losing connection to the Tango device"""


@dataclass
class MonitoredAttribute:
    """Package together the information needed for a subscription"""

    attr_name: str
    subscription_id: Optional[int] = None

    def subscribe(
        self,
        device_proxy: tango.DeviceProxy,
        subscription_callback: Optional[Callable] = None,
    ):
        """Subscribe to change events for this attribute

        :param device_proxy: The tango device proxy
        :type device_proxy: tango.DeviceProxy
        :param subscription_callback: Event callback subscription,
            defaults to None
        :type subscription_callback: Optional[Callable], optional
        """
        # State has to be monitored since we use it to keep track
        # of communication state
        if self.attr_name == "State":
            if not device_proxy.is_attribute_polled("State"):
                device_proxy.poll_attribute("State", STATE_ATTR_POLL_PERIOD)
        self.unsubscribe(device_proxy)
        self.subscription_id = device_proxy.subscribe_event(
            self.attr_name, tango.EventType.CHANGE_EVENT, subscription_callback
        )

    def unsubscribe(self, device_proxy: tango.DeviceProxy):
        """Unsubscribe from change events

        :param device_proxy: The tango DeviceProxy
        :type device_proxy: tango.DeviceProxy
        """
        if self.subscription_id:
            try:
                device_proxy.unsubscribe_event(self.subscription_id)
            except (tango.EventSystemFailed, KeyError):
                # If the device went away, we may have lost the sub
                pass
        self.subscription_id = None


class TangoDeviceComponentManager(TaskExecutorComponentManager):
    """A component manager for a Tango device

    Upon class instantiation, a method that tries to connect to the Tango
    device is passed on to a worker thread. The connection will be retried
    every `SLEEP_TIME_BETWEEN_RECONNECTS` seconds. Upon success the
    thread exists and the communication state is set to ESTABLISHED.

    The communication state is monitored by utilising a subscription to the
    change events on `State`. If the Tango device goes down an error event
    is generated and the communication state is set to NOT_ESTABLISHED.
    Reconnection will then be attempted.

    Note that in local testing the event that indicates that connection
    to the device is lost can take up to 15s to fire. Due to this latency
    a method is made available that will execute a command on the device,
    but first check that the device is up. If not a `LostConnection`
    exception is thrown and the communication state set to `NOT_ESTABLISHED`
    Reconnection will then be attempted.
    """

    def __init__(
        self,
        tango_device_fqdn: AnyStr,
        logger,
        *args,
        max_workers: Optional[int] = None,
        communication_state_callback: Optional[Callable] = None,
        component_state_callback: Optional[Callable] = None,
        **kwargs,
    ):
        self.tango_device_fqdn: str = tango_device_fqdn
        self._device_proxy: Optional[tango.DeviceProxy] = None
        self._monitored_attributes: List[MonitoredAttribute] = [
            MonitoredAttribute("State")
        ]
        self.latest_event_message_timestamp = datetime.now().isoformat()

        super().__init__(
            logger,
            *args,
            max_workers=max_workers,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            **kwargs,
        )

        # Init the component state
        self._component_state["connection_in_progress"] = False
        for monitored_state in self._monitored_attributes:
            self._component_state[monitored_state.attr_name] = "UNKNOWN"

    def start_communicating(self):
        """
        Create the DeviceProxy in a thread, retrying until we are successful
        """
        if not self.component_state["connection_in_progress"]:
            self.logger.info(
                "Starting communication to [%s]", self.tango_device_fqdn
            )
            self._update_component_state(connection_in_progress=True)
            self.submit_task(
                self._create_device_proxy,
                args=[self.tango_device_fqdn, self._device_proxy],
                task_callback=self._device_proxy_creation_cb,
            )

    def _check_connection(func):  # pylint: disable=E0213
        """Connection check decorator.

        This is a workaround for decorators in classes.

        Execute the method, if communication fails, commence reconnection.
        """

        def _decorator(self, *args, **kwargs):
            try:
                if self.communication_state != CommunicationStatus.ESTABLISHED:
                    raise LostConnection(
                        "Communication status not ESTABLISHED"
                    )
                if not self._device_proxy:  # pylint: disable=W0212
                    raise LostConnection("DeviceProxy not created")
                return func(self, *args, **kwargs)  # pylint: disable=E1102
            except (tango.ConnectionFailed, LostConnection) as err:
                self.start_communicating()  # pylint: disable=W0212
                raise LostConnection(
                    f"[{self.tango_device_fqdn}]"  # pylint: disable=W0212
                    "  not connected. Retry in progress"
                ) from err

        return _decorator

    @classmethod
    def _create_device_proxy(
        cls,
        tango_device_fqdn: AnyStr,
        device_proxy: Optional[tango.DeviceProxy],
        task_abort_event: Event = None,
        task_callback: Callable = None,
    ):
        """
        Keep trying to create the device proxy, retrying every
        `SLEEP_TIME_BETWEEN_RECONNECTS` seconds

        This method should be passed to ThreadPoolExecutor

        :param tango_device_fqdn: Address of the Tango device
        :type tango_device_fqdn: AnyStr
        :param device_proxy: A DeviceProxy if it exists, if none it will
            be created
        :type device_proxy: Optional[tango.DeviceProxy]
        :param task_abort_event: Check whether tasks have been aborted
        :type task_abort_event: Event, optional
        :param task_callback: Callback to report status
        :type task_callback: Callable, optional
        """
        with tango.EnsureOmniThread():
            try:
                task_callback(status=TaskStatus.IN_PROGRESS)
                retry_count = 0
                while True:
                    # Leave thread if aborted
                    if task_abort_event and task_abort_event.is_set():
                        task_callback(status=TaskStatus.ABORTED, result=None)
                        return

                    try:
                        retry_count += 1
                        if not device_proxy:
                            device_proxy = tango.DeviceProxy(tango_device_fqdn)
                        device_proxy.ping()
                        task_callback(
                            status=TaskStatus.COMPLETED, result=device_proxy
                        )
                        return

                    except tango.DevFailed:
                        task_callback(
                            status=TaskStatus.IN_PROGRESS,
                            retry_count=retry_count,
                        )
                        time.sleep(SLEEP_TIME_BETWEEN_RECONNECTS)
            # Broad except otherwise this code fails silently
            except Exception as err:  # pylint: disable=W0703
                task_callback(status=TaskStatus.FAILED, result=err)

    def _device_proxy_creation_cb(
        self,
        status: TaskStatus,
        result: Optional[Any] = None,
        retry_count: int = 0,
        message: Optional[Any] = None,
    ):
        """Callback to be called as _create_device_proxy runs

        :param status: The result of the task
        :type status: TaskStatus
        :param result: Either None or the DeviceProxy
        :type result: Optional[DeviceProxy]
        :param retry_count: The number of connection retries
        :type retry_count: int
        """
        self.logger.debug(
            "Device Proxy creation callback [%s, %s, %s, %s]",
            status,
            result,
            retry_count,
            message,
        )

        if status == TaskStatus.QUEUED:
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )

        if status == TaskStatus.COMPLETED:
            self._update_component_state(connection_in_progress=False)
            with tango.EnsureOmniThread():
                if not self._device_proxy:
                    self._device_proxy = result

                # If the device went away completely we may have
                # lost or subscriptions, redo them
                for monitored_attr in self._monitored_attributes:
                    monitored_attr.subscribe(
                        self._device_proxy,
                        self._subscription_event_callback,
                    )
                self._update_communication_state(
                    CommunicationStatus.ESTABLISHED
                )
                self.logger.info(
                    "Comms established to [%s]", self.tango_device_fqdn
                )

        if status == TaskStatus.ABORTED:
            self.logger.info("Device Proxy creation task aborted")

        if status == TaskStatus.FAILED:
            if isinstance(result, Exception):
                self.logger.exception(result)
            else:
                self.logger.error(
                    "Device Proxy creation task failed [%s]", result
                )

        if retry_count:
            self.logger.info(
                "Connection retry count [%s] for device [%s]",
                retry_count,
                self.tango_device_fqdn,
            )

    def _subscription_event_callback(self, event_data: tango.EventData):
        """Try to reconnect if the State event has an error.

        Otherwise just updates state

        :param event_data: The event data
        :type event_data: EventData
        """
        self.logger.debug(f"Event callback [{event_data}]")

        # We tend to get error events after comms have been reestablished.
        # Ignore the error events if it's older than a valid event
        if event_data.attr_value:
            event_time_stamp = event_data.attr_value.time.isoformat()
        else:
            event_time_stamp = event_data.reception_date.isoformat()
            if event_time_stamp < self.latest_event_message_timestamp:
                return

        self.latest_event_message_timestamp = event_time_stamp

        if self.communication_state == CommunicationStatus.NOT_ESTABLISHED:
            return

        if event_data.err:
            new_state = {}
            for component_state_name in self._component_state:
                if component_state_name == "connection_in_progress":
                    continue
                new_state[component_state_name] = "UNKNOWN"
            self._update_component_state(**new_state)
            self.start_communicating()
            return

        attr_name = event_data.attr_value.name

        # Add it so component state if not there
        if attr_name not in self._component_state:
            self._component_state[attr_name] = None

        self._update_component_state(
            **{attr_name: str(event_data.attr_value.value)}
        )

    def _unsubscribe_events(self):
        """Attempt to unsubscribe event subscriptions"""
        for monitored_attr in self._monitored_attributes:
            monitored_attr.unsubscribe(self._device_proxy)

    def stop_communicating(self, aborted_callback: Optional[Callable] = None):
        """Break off communication with the device.

        :param aborted_callback: callback to call when abort completes,
            defaults to None
        :type aborted_callback: Optional[Callable], optional
        """
        with tango.EnsureOmniThread():
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )
            self._unsubscribe_events()
            self._device_proxy = None
            self.abort_tasks(aborted_callback)

    @_check_connection
    def run_device_command(
        self, command_name: AnyStr, command_arg: Optional[Any] = None
    ) -> Any:
        """Attempt to run `command_name` on the Tango device.

        If the connection failed
            - Mark `communication_state` as NOT_ESTABLISHED
            - Kick off the reconnect attempts

        :param command_name: The Tango command to run
        :type command_name: AnyStr
        :param command_arg: The Tango command parameter
        :type command_arg: Optional Any
        """
        with tango.EnsureOmniThread():
            result = self._device_proxy.command_inout(
                command_name, command_arg
            )
            self.logger.info(
                "Result of [%s] on [%s] is [%s]",
                command_name,
                self.tango_device_fqdn,
                result,
            )
            return result

    @_check_connection
    def monitor_attribute(self, attribute_name: str):
        """Update the component state with the Attribute value as it changes

        :param attribute_name: Attribute to keep track of
        :type attribute_name: str
        """
        monitored_attribute = MonitoredAttribute(attribute_name)
        monitored_attribute.subscribe(
            self._device_proxy,
            subscription_callback=self._subscription_event_callback,
        )
        self._monitored_attributes.append(monitored_attribute)

    @_check_connection
    def unmonitor_attribute(self, attribute_name: str):
        """Stop monitoring an attribute

        :param attribute_name: Attribute to stop monitoring
        :type attribute_name: str
        """
        for monitored_attribute in self._monitored_attributes:
            if monitored_attribute.attr_name == attribute_name:
                monitored_attribute.unsubscribe(self._device_proxy)
                self._monitored_attributes.remove(monitored_attribute)
