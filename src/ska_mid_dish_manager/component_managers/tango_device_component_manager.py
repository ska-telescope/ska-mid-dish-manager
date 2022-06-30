# pylint: disable=W0223
"""Component Manager for a Tango device"""
import logging
import time
from threading import Event
from typing import Any, AnyStr, Callable, Optional

from ska_tango_base.base.component_manager import TaskExecutorComponentManager
from ska_tango_base.control_model import CommunicationStatus
from ska_tango_base.executor import TaskStatus
from tango import DevFailed, DeviceProxy, EventData, EventType

SLEEP_TIME_BETWEEN_RECONNECTS = 1  # seconds


class TangoDeviceComponentManager(TaskExecutorComponentManager):
    """A component manager for a Tango device"""

    def __init__(
        self,
        tango_device_fqdn: AnyStr,
        *args,
        max_workers: Optional[int] = None,
        **kwargs
    ):
        self._tango_device_fqdn = tango_device_fqdn
        self._device_proxy = None
        self._state_subscription_id = None
        super().__init__(
            *args,
            max_workers=max_workers,
            communication_state_callback=self._communication_state_cb,
            component_state_callback=self._component_state_cb,
            **kwargs
        )
        self.start_communicating()

    def _communication_state_cb(self):
        pass

    def _component_state_cb(self):
        pass

    def start_communicating(self):
        """
        Create the DeviceProxy in a thread
        """
        self.submit_task(
            self._create_device_poxy,
            args=[self._tango_device_fqdn, self.logger],
            task_callback=self._device_proxy_creation_cb,
        )

    def _state_subscription_event_callback(self, event_data: EventData):
        if event_data.err:
            self.communication_state = CommunicationStatus.NOT_ESTABLISHED
        else:
            self.communication_state = CommunicationStatus.ESTABLISHED

    def _device_proxy_creation_cb(
        self, status: TaskStatus, result: Any = None, retry_count=0
    ):
        """Callback to be called as _create_device_poxy runs

        :param status: The result of the task
        :type status: TaskStatus
        :param result: Either None or the DeviceProxy
        :type result: Optional[DeviceProxy]
        """
        if status == TaskStatus.COMPLETED and isinstance(result, DeviceProxy):
            self._device_proxy = result
            self._state_subscription_id = self._device_proxy.subscribe_event(
                "State",
                EventType.CHANGE_EVENT,
                self._state_subscription_event_callback,
            )

        if status == TaskStatus.QUEUED:
            self.logger.info("Device Proxy creation task queued")

        if status == TaskStatus.ABORTED:
            self.logger.info("Device Proxy creation task aborted")

        if status == TaskStatus.FAILED and isinstance(result, Exception):
            self.logger.exception(result)
            if retry_count:
                self.logger.info("Retry count [%s]", retry_count)

        if status == TaskStatus.FAILED and not isinstance(result, Exception):
            self.logger.error("Device Proxy creation task failed [%s]", result)
            if retry_count:
                self.logger.info("Retry count [%s]", retry_count)

    @classmethod
    def _create_device_poxy(
        cls,
        tango_device_fqdn: AnyStr,
        _: logging.Logger,
        task_abort_event: Event = None,
        task_callback: Callable = None,
    ):
        """
        Keep trying to create the device proxy, retrying every
        `SLEEP_TIME_BETWEEN_RECONNECTS` seconds

        This method should be passed to ThreadPoolExecutor
        """
        retry_count = 0
        while True:

            # If we ever need to abort this task
            if task_abort_event and task_abort_event.is_set():
                task_callback(status=TaskStatus.ABORTED, result=None)
                return
            try:
                retry_count += 1
                device_proxy = DeviceProxy(tango_device_fqdn)
                task_callback(status=TaskStatus.COMPLETED, result=device_proxy)
                return
            except DevFailed as connect_error:
                task_callback(
                    status=TaskStatus.FAILED,
                    result=connect_error,
                    retry_count=retry_count,
                )
                time.sleep(SLEEP_TIME_BETWEEN_RECONNECTS)

    def stop_communicating(self):
        self.abort_tasks()
        if self._state_subscription_id and self._device_proxy:
            self._device_proxy.unsubscribe_event(self._state_subscription_id)

    def standby(self, task_callback: Callable):
        pass

    def reset(self, task_callback: Callable):
        pass
