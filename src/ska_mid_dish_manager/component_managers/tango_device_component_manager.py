# pylint: disable=W0223
"""Component Manager for a Tango device

Upon class instantiation, a method that tries to connect to the Tango
device is passed on to a worker thread. The connection will be retried
every `SLEEP_TIME_BETWEEN_RECONNECTS` seconds. Upon success the
thread exists and the communication state is set to ESTABLISHED.

The communication state is monitored by utilising a subscription to the
change events on State. If the Tango device goes down an error event
is generated and the communication state is set to NOT_ESTABLISHED

The method `run_device_command` will set the communication state
to NOT_ESTABLISHED if the Tango command fails

"""
import time
from threading import Event
from typing import Any, AnyStr, Callable, Optional

import tango
from ska_tango_base.base.component_manager import TaskExecutorComponentManager
from ska_tango_base.control_model import CommunicationStatus
from ska_tango_base.executor import TaskStatus

SLEEP_TIME_BETWEEN_RECONNECTS = 1  # seconds
STATE_ATTR_POLL_PERIOD = 3000


class LostConnection(Exception):
    """Exception for losing connection to the Tango device"""


class TangoDeviceComponentManager(TaskExecutorComponentManager):
    """A component manager for a Tango device"""

    def __init__(
        self,
        tango_device_fqdn: AnyStr,
        *args,
        max_workers: Optional[int] = None,
        communication_state_callback: Optional[Callable] = None,
        component_state_callback: Optional[Callable] = None,
        **kwargs,
    ):
        self._tango_device_fqdn = tango_device_fqdn
        self._device_proxy = None
        self._state_subscription_id = None
        self._connect_in_progress = False
        super().__init__(
            *args,
            max_workers=max_workers,
            communication_state_callback=communication_state_callback,
            component_state_callback=component_state_callback,
            **kwargs,
        )
        self.start_communicating()

    def start_communicating(self):
        """
        Create the DeviceProxy in a thread, retrying until we are successful
        """
        if not self._connect_in_progress:
            self.submit_task(
                self._create_device_proxy,
                args=[self._tango_device_fqdn, self._device_proxy],
                task_callback=self._device_proxy_creation_cb,
            )

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
        task_callback(status=TaskStatus.IN_PROGRESS, retry_count=0)
        with tango.EnsureOmniThread():
            try:
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
            # Broad except otherwise this code may fail silently
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

        if status == TaskStatus.IN_PROGRESS:
            self._connect_in_progress = True
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )
        else:
            self._connect_in_progress = False

        if status == TaskStatus.QUEUED:
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )

        if status == TaskStatus.COMPLETED:
            with tango.EnsureOmniThread():
                self._device_proxy = result
                # Try and subscribe to State, if not polled, the enable polling
                try:
                    if not self._device_proxy.get_attribute_poll_period(
                        "State"
                    ):
                        self._device_proxy.poll_attribute(
                            "State", STATE_ATTR_POLL_PERIOD
                        )

                    self._state_subscription_id = (
                        self._device_proxy.subscribe_event(
                            "State",
                            tango.EventType.CHANGE_EVENT,
                            self._state_subscription_event_callback,
                        )
                    )
                    self._update_communication_state(
                        CommunicationStatus.ESTABLISHED
                    )
                except tango.CommunicationFailed:
                    self.start_communicating()

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
            self.logger.info("Connection retry count [%s]", retry_count)

    def _state_subscription_event_callback(self, event_data: tango.EventData):
        """Updates communication_state when the State subscription sends an event

        :param event_data: The event data
        :type event_data: EventData
        """
        self.logger.debug(f"Status event callback [{event_data}]")
        if event_data.err:
            # Try to reconnect when connection lost
            self.start_communicating()
        else:
            self._update_communication_state(CommunicationStatus.ESTABLISHED)

    def stop_communicating(self):
        with tango.EnsureOmniThread():
            self._update_communication_state(
                CommunicationStatus.NOT_ESTABLISHED
            )
            self.abort_tasks()
            if self._state_subscription_id and self._device_proxy:
                try:
                    self._device_proxy.unsubscribe_event(
                        self._state_subscription_id
                    )
                except tango.DevFailed:
                    # If the device restarted the subscription will not be
                    # registered
                    pass
            self._device_proxy = None
            self._state_subscription_id = None

    def run_device_command(
        self, command_name: AnyStr, command_arg: Optional[Any] = None
    ) -> Any:
        """Attempt to run `command_name` on the Tango device.

        If the connection failed
            - Mark `communication_state` as NOT_ESTABLISHED
            - Kick off the reconnect attempts

        :param command_name: The Tango command to run
        :type command_name: AnyStr
        :param command_arg: The Tango command paramater
        :type command_arg: Optional Any
        """
        try:
            if self.communication_state != CommunicationStatus.ESTABLISHED:
                raise LostConnection(
                    "Communication status not CommunicationStatus.ESTABLISHED"
                )
            if not self._device_proxy:
                raise LostConnection("DeviceProxy not created")
            with tango.EnsureOmniThread():
                return self._device_proxy.command_inout(
                    command_name, command_arg
                )
        except (tango.ConnectionFailed, LostConnection) as err:
            self.start_communicating()
            raise LostConnection(
                f"Connection to [{self._tango_device_fqdn}] not established. "
                "Retrying connection"
            ) from err
