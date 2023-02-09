""" This module contains Subscription that is responsible for creating a
    Tango DeviceProxy and subscibing to a attribute.
    All events are passed onto the event queue for processing in the
    TangoDeviceComponentManager.
"""

import enum
import logging
import time
from queue import Queue
from threading import Event, Lock
from typing import AnyStr, Callable, Optional

import tango
from ska_control_model import TaskStatus
from ska_tango_base.executor import TaskExecutor

from ska_mid_dish_manager.component_managers.monitored_attribute import (
    MonitoredAttribute,
    ReceivedErrorEvent,
)

SLEEP_BETWEEN_RECONNECTS = 0.5


class ConnectionState(enum.IntEnum):
    DISCONNECTED = 0
    CONNECTING = 1
    MONITORING = 2


class Subscription:
    def __init__(
        self,
        tango_device_fqdn: str,
        event_queue: Queue,
        attribute_name: str,
        # self._update_communication_state(CommunicationStatus.NOT_ESTABLISHED)
        update_communication_state_cb: Callable,
        logger: logging.Logger = None,
    ) -> None:
        """Subscription created device proxy and subscribes an attr

        :param tango_device_fqdn: Tango device name,
            defaults to ""
        :type tango_device_fqdn: str, optional
        :param event_queue: All events recieved goes there for processing,
            defaults to None
        :type event_queue: Queue, optional
        :param logger: logger, defaults to None
        :type logger: logging.Logger, optional
        """
        if not logger:
            logger = logging.getLogger()
        self._logger = logger
        self._tango_device_fqdn = tango_device_fqdn
        self._event_queue = event_queue
        self._attribute_name = attribute_name
        self._update_communication_state_cb = update_communication_state_cb
        self._task_executor = TaskExecutor(max_workers=1)
        self._update_comm_state_lock = Lock()

        self.connection_state = ConnectionState.DISCONNECTED
        self.connected_event = Event()
        self.disconnected_event = Event()
        self.disconnected_event.set()

    def connect(self):
        """Create device proxy and subscribe to attribute"""
        self._logger.info(
            "Started connecting on [%s] to [%s]", self._tango_device_fqdn, self._attribute_name
        )
        if self.connection_state != ConnectionState.DISCONNECTED:
            raise RuntimeError("You can only connect when disconnected")

        self.connection_state = ConnectionState.CONNECTING

        # Start the device proxy creation
        self._task_executor.submit(
            self._subscribe_to_attr,
            args=[
                self._tango_device_fqdn,
                self._attribute_name,
                self._logger,
                self._event_queue,
                _update_comm_state_lock,
                _update_communication_state_cb,
            ],
            kwargs=None,
            task_callback=self._subscribed_to_attr_cb,
        )

    @classmethod
    def _subscribe_to_attr(  # pylint: disable=too-many-arguments
        self,
        tango_device_fqdn: AnyStr,
        attribute_name: AnyStr,
        logger: logging.Logger,
        event_queue: Queue,
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
        if task_callback:
            task_callback(status=TaskStatus.IN_PROGRESS)
        retry_count = 0
        while True:
            # Leave thread if aborted
            if task_abort_event and task_abort_event.is_set():
                task_callback(status=TaskStatus.ABORTED, result=None)
                return

            try:
                retry_count += 1
                device_proxy = tango.DeviceProxy(tango_device_fqdn)
                device_proxy.ping()
                task_callback(progress=f"DeviceProxy created to {tango_device_fqdn}")
                monitored_attribute = MonitoredAttribute(attribute_name, event_queue)
                monitored_attribute.monitor(device_proxy, logger, task_abort_event, task_callback)
                self.connection_state = ConnectionState.MONITORING

            except tango.DevFailed as err:
                logger.exception(err)
                task_callback(
                    progress=(
                        f"Retrying connection to {attribute_name} on "
                        f"{tango_device_fqdn} count {retry_count}"
                    ),
                    retry_count=retry_count,
                )
                time.sleep(SLEEP_BETWEEN_RECONNECTS)

            except ReceivedErrorEvent as err:
                logger.exception(err)
                task_callback(
                    progress=(
                        f"Got an error event on {attribute_name} on "
                        f"{tango_device_fqdn} count {retry_count}"
                    ),
                    retry_count=retry_count,
                )
                logger.info(
                    "Disconnecting %s on %s due to error event",
                    self._attribute_name,
                    self._tango_device_fqdn,
                )
                self.disconnect()
                # Wait a bit before reconnecting
                time.sleep(SLEEP_BETWEEN_RECONNECTS)
                while self.disconnected_event.wait(1):
                    logger.info(
                        "Waiting for disconnected event for %s on %s",
                        self._attribute_name,
                        self._tango_device_fqdn,
                    )
                self.connect()

    def _subscribed_to_attr_cb(self, status=TaskStatus, *args, **kwargs):
        self._logger.info("_subscribed_to_attr_cb [%s], [%s]", args, kwargs)
        if status == TaskStatus.IN_PROGRESS:
            self.connected_event.set()
            self.disconnected_event.clear()

    def disconnect(self):
        """Abort tasks and connect"""
        self._logger.info(
            "Disconnecting from [%s] on [%s]", self._attribute_name, self._tango_device_fqdn
        )
        self._task_executor.abort(task_callback=self._aborted_cb)

    def _aborted_cb(self, status: TaskStatus, *args, **kwargs):
        """Once aborted is completed. Recreate the Device Proxy and subscribe"""
        self._logger.info("_aborted_cb [%s] [%s], [%s]", status, args, kwargs)
        if status == TaskStatus.COMPLETED:
            self.connection_state = ConnectionState.DISCONNECTED
            self.connected_event.clear()
            self.disconnected_event.set()
            self._logger.info(
                "Disconnecting from [%s] on [%s]", self._attribute_name, self._tango_device_fqdn
            )
