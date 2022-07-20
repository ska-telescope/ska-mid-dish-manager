"""Generic component manager for a subservient tango device"""
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from queue import Empty, Queue
from threading import Event
from typing import Any, AnyStr, Callable, List, Optional

import tango
from ska_tango_base.base.component_manager import TaskExecutorComponentManager
from ska_tango_base.control_model import CommunicationStatus
from ska_tango_base.executor import TaskStatus
from transitions import Machine

SLEEP_TIME_BETWEEN_RECONNECTS = 1  # seconds
STATE_ATTR_POLL_PERIOD = 3000


def _check_connection(func):  # pylint: disable=E0213
    """Connection check decorator.

    This is a workaround for decorators in classes.

    Execute the method, if communication fails, commence reconnection.
    """

    def _decorator(self, *args, **kwargs):
        try:
            if self.communication_state != CommunicationStatus.ESTABLISHED:
                raise LostConnection("Communication status not ESTABLISHED")
            if not self._device_proxy:  # pylint: disable=W0212
                raise LostConnection("DeviceProxy not created")
            return func(self, *args, **kwargs)  # pylint: disable=E1102
        except (tango.ConnectionFailed, LostConnection) as err:
            self.reconnect()  # pylint: disable=W0212
            raise LostConnection(
                f"[{self._tango_device_fqdn}]"  # pylint: disable=W0212
                "  not connected. Retry in progress"
            ) from err

    return _decorator


class LostConnection(Exception):
    """Exception for losing connection to the Tango device"""


@dataclass
class MonitoredAttribute:
    """Package together the information needed for a subscription"""

    attr_name: str
    event_queue: Queue
    subscription_id: Optional[int] = None

    def _subscription_callback(self, event_data: tango.EventData):
        self.event_queue.put(event_data, timeout=10)

    def monitor(
        self,
        device_proxy,
        task_abort_event: Optional[Event] = None,
        task_callback: Optional[Callable] = None,  # pylint: disable=W0613
    ):
        """Manage attribute event subscription"""
        with tango.EnsureOmniThread():
            if self.attr_name == "State":
                if not device_proxy.is_attribute_polled("State"):
                    device_proxy.poll_attribute(
                        "State", STATE_ATTR_POLL_PERIOD
                    )
            self.subscription_id = device_proxy.subscribe_event(
                self.attr_name,
                tango.EventType.CHANGE_EVENT,
                self._subscription_callback,
            )
            while not task_abort_event.is_set():
                time.sleep(1)
            device_proxy.unsubscribe_event(self.subscription_id)


# pylint: disable=abstract-method, too-many-instance-attributes
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
        communication_state_callback: Optional[Callable] = None,
        component_state_callback: Optional[Callable] = None,
        **kwargs,
    ):
        self._communication_state_callback = communication_state_callback
        self._component_state_callback = component_state_callback
        self._events_queue = Queue()
        self._tango_device_fqdn = tango_device_fqdn
        self._device_proxy = None
        if not logger:
            logger = logging.getLogger()
        self.logger = logger
        self._monitored_attributes: List[MonitoredAttribute] = [
            MonitoredAttribute("State", self._events_queue)
        ]

        states = [
            "disconnected",
            "setting_up_device_proxy",
            "connected",
            "setting_up_monitoring",
            "monitoring",
        ]

        self._state_machine = Machine(
            model=self,
            states=states,
            initial="disconnected",
        )
        self._state_machine.add_ordered_transitions()

        super().__init__(
            logger,
            *args,
            max_workers=100,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            connection_state="disconnected",
            **kwargs,
        )

        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
        self._start_event_handling_thread()

    def _update_state_from_event(self, event_data: tango.EventData):
        if event_data.err:
            # We lost connection, get the connection bask
            self.reconnect()
        else:
            attr_name = event_data.attr_value.name

            # Add it so component state if not there
            if attr_name not in self._component_state:
                self._component_state[attr_name] = None

            self._update_component_state(
                **{attr_name: str(event_data.attr_value.value)}
            )

    @classmethod
    def _event_handler(
        cls,
        event_queue: Queue,
        update_state_cb: Callable,
        task_abort_event: Optional[Event] = None,
        task_callback: Optional[Callable] = None,
    ):
        if task_callback:
            task_callback(status=TaskStatus.IN_PROGRESS)
        latest_event_message_timestamp = datetime.utcnow().isoformat()
        while task_abort_event and not task_abort_event.is_set():
            try:
                event_data = event_queue.get(timeout=1)
                if event_data.attr_value:
                    event_time_stamp = event_data.attr_value.time.isoformat()
                else:
                    event_time_stamp = event_data.reception_date.isoformat()
                    # Sometimes we get late connection lost messages, filter
                    if event_time_stamp < latest_event_message_timestamp:
                        continue
                update_state_cb(event_data)
            except Empty:
                pass
        if task_callback:
            task_callback(status=TaskStatus.ABORTED)

    def _kill_monitoring_threads(self):
        # Set the abort event
        # Wait for completion
        self.logger.info("Killing mmonitoring threads")

    def _start_monitoring_threads(self):
        # Start the monitroing threads
        self.logger.info("Starting mmonitoring threads")
        for monitored_attribute in self._monitored_attributes:
            self.submit_task(
                monitored_attribute.monitor,
                args=[self._device_proxy],
                task_callback=None,
            )

    def _start_event_handling_thread(self):
        self.submit_task(
            self._event_handler,
            args=[self._events_queue, self._update_state_from_event],
            task_callback=None,
        )

    def _device_proxy_creation_cb(
        self,
        status: TaskStatus,
        result: Optional[Any] = None,
        retry_count: int = 0,
        message: Optional[Any] = None,
    ):
        """Callback to be called as _create_device_proxy runs

        :param: status: The result of the task
        :type: status: TaskStatus
        :param: result: Either None or the DeviceProxy
        :type: result: Optional[DeviceProxy]
        :param: retry_count: The number of connection retries
        :type: retry_count: int
        """
        # pylint: disable=no-member
        self.logger.debug(
            "Device Proxy creation callback [%s, %s, %s, %s]",
            status,
            result,
            retry_count,
            message,
        )

        if status == TaskStatus.COMPLETED:
            if not self._device_proxy:
                self._device_proxy = result
            self.to_connected()

        if status == TaskStatus.ABORTED:
            self.logger.info("Device Proxy creation task aborted")

        if status == TaskStatus.FAILED:
            if isinstance(result, Exception):
                self.logger.error(result)
            else:
                self.logger.error(
                    "Device Proxy creation task failed [%s]", result
                )

        if retry_count:
            self.logger.info(
                "Connection retry count [%s] for device [%s]",
                retry_count,
                self._tango_device_fqdn,
            )

    @classmethod
    def _create_device_proxy(  # pylint: disable=too-many-arguments
        cls,
        tango_device_fqdn: AnyStr,
        device_proxy: Optional[tango.DeviceProxy] = None,
        task_abort_event: Event = None,
        task_callback: Callable = None,
    ):
        """
        Keep trying to create the device proxy, retrying every
        `SLEEP_TIME_BETWEEN_RECONNECTS` seconds

        This method should be passed to ThreadPoolExecutor

        :param: tango_device_fqdn: Address of the Tango device
        :type: tango_device_fqdn: AnyStr
        :param: device_proxy: A DeviceProxy if it exists, if none it will
            be created
        :type: device_proxy: Optional[tango.DeviceProxy]
        :param: task_abort_event: Check whether tasks have been aborted
        :type: task_abort_event: Event, optional
        :param: task_callback: Callback to report status
        :type: task_callback: Callable, optional
        """
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
                task_callback(status=TaskStatus.COMPLETED, result=device_proxy)
                return

            except tango.DevFailed:
                task_callback(
                    status=TaskStatus.IN_PROGRESS,
                    retry_count=retry_count,
                )
                time.sleep(SLEEP_TIME_BETWEEN_RECONNECTS)

    @_check_connection
    def run_device_command(
        self, command_name: AnyStr, command_arg: Optional[Any] = None
    ) -> Any:
        """Attempt to run `command_name` on the Tango device.

        If the connection failed
            - Mark `communication_state` as NOT_ESTABLISHED
            - Kick off the reconnect attempts

        :param: command_name: The Tango command to run
        :type: command_name: AnyStr
        :param: command_arg: The Tango command parameter
        :type: command_arg: Optional Any
        """
        result = self._device_proxy.command_inout(command_name, command_arg)
        self.logger.info(
            "Result of [%s] on [%s] is [%s]",
            command_name,
            self._tango_device_fqdn,
            result,
        )
        return result

    @_check_connection
    def monitor_attribute(self, attribute_name: str):
        """Update the component state with the Attribute value as it changes

        :param: attribute_name: Attribute to keep track of
        :type: attribute_name: str
        """
        monitored_attribute = MonitoredAttribute(
            attribute_name, self._events_queue
        )
        self._monitored_attributes.append(monitored_attribute)
        self.submit_task(
            monitored_attribute.monitor,
            args=[self._device_proxy],
            task_callback=None,
        )

    def reconnect(self):
        """Reconnect to the device"""
        self.logger.info("Reconnecting")
        self.start_communicating()

    def start_communicating(self):
        """Establish communication with the device"""
        # pylint: disable=no-member
        self.logger.info("start_communicating")
        self.to_disconnected()
        self.next_state()  # setting_up_device_proxy

    def stop_communicating(self):
        """Stop communication with the device"""
        # pylint: disable=no-member
        self.to_disconnected()

    def on_enter_disconnected(self):
        """Disconnect from current communication with the device"""
        self.logger.info("in on_enter_disconnected")
        self._update_component_state(connection_state="disconnected")
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
        self._kill_monitoring_threads()

    def on_enter_setting_up_device_proxy(self):
        """Set up a connection to the device through the proxy"""
        self.logger.info("in on_enter_setting_up_device_proxy")
        self._update_component_state(
            connection_state="setting_up_device_proxy"
        )
        # Start the device proxy creation
        self.submit_task(
            self._create_device_proxy,
            args=[
                self._tango_device_fqdn,
                self._device_proxy,
            ],
            task_callback=self._device_proxy_creation_cb,
        )

    def on_enter_connected(self):
        """Update component state when connection is established"""
        # pylint: disable=no-member
        self.logger.info("in on_enter_connected")
        self._update_component_state(connection_state="connected")
        # Just go to next state
        self.next_state()

    def on_enter_setting_up_monitoring(self):
        """Set up monitoring after connection"""
        # pylint: disable=no-member
        self.logger.info("in on_enter_setting_up_monitoring")
        self._update_component_state(connection_state="setting_up_monitoring")
        self._start_monitoring_threads()
        self.next_state()

    def on_enter_monitoring(self):
        """Transition to monitoring after setup is complete"""
        self.logger.info("in on_enter_monitoring")
        self._update_component_state(connection_state="monitoring")
        self._update_communication_state(CommunicationStatus.ESTABLISHED)

    def on_exit_monitoring(self):
        """Update communication state after monitoring is closed"""
        self.logger.info("in on_exit_monitoring")
        self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
