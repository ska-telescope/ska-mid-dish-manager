"""A factory for creating and managing tango device proxies"""

import logging
from threading import Event
from typing import Any, Dict, Optional

import tango


class DeviceProxyManager:
    """
    Manage tango.DeviceProxy with a connection to the device server

    Too many device proxy objects to the same server is unnecessary and probably
    risky; i.e. any device proxy thread dying can crash the device server process

    Note: The caller should wrap the call in tango.EnsureOmniThread
    """

    def __init__(self, logger: logging.Logger):
        self._logger = logger
        self.device_proxies: Dict[str, tango.DeviceProxy] = {}

    def __call__(self, trl: str, thread_event: Optional[Event] = None) -> Any:
        device_proxy = self.device_proxies.get(trl)

        if device_proxy is not None:
            if not self._is_tango_device_running(device_proxy):
                self._wait_for_device(device_proxy, thread_event=thread_event)
            return device_proxy

        device_proxy = self.create_tango_device_proxy(trl, thread_event=thread_event)
        return device_proxy

    def _is_tango_device_running(self, tango_device_proxy: tango.DeviceProxy) -> bool:
        """Checks if the TANGO device server is running.

        :param tango_device_proxy: a client to the device server
        :type tango_device_proxy: tango.DeviceProxy

        :returns: is_device_running (boolean)
        """
        try:
            tango_device_proxy.ping()
        except tango.DevFailed:
            self._logger.exception(f"Failed to ping device proxy: {tango_device_proxy.dev_name()}")
            is_device_running = False
        else:
            is_device_running = True

        return is_device_running

    def _wait_for_device(
        self,
        tango_device_proxy: tango.DeviceProxy,
        retry_time: float = 0.5,
        thread_event: Optional[Event] = None,
    ) -> None:
        """
        Wait until it the client has established a connection with the
        device server and/or for the device server to be up and running.

        :param tango_device_proxy: a client to the device server
        :type tango_device_proxy: tango.DeviceProxy
        :param retry_time: waits between reconnection attempts
        :type retry_time: int
        :param thread_event: communicate with thread from a signal
        :type thread_event: threading.Event

        :returns: None
        """
        is_device_connected = False
        while not is_device_connected and (thread_event and not thread_event.is_set()):
            try:
                tango_device_proxy.reconnect(True)
            except tango.DevFailed:
                self._logger.exception(
                    f"Failed to reconnect to device proxy: {tango_device_proxy.dev_name()}"
                )
                self._logger.debug(f"Attempting reconnection to the device proxy in {retry_time}s")
                if thread_event:
                    thread_event.wait(timeout=retry_time)
            else:
                is_device_connected = True

    def create_tango_device_proxy(
        self, trl: str, retry_time: float = 0.5, thread_event: Optional[Event] = None
    ) -> Any:
        """
        Wait until it the sub component manager has established a connection
        with the device server and/or for the device server to be up and running.

        :param tango_device_proxy: a client to the device server
        :type tango_device_proxy: tango.DeviceProxy
        :param retry_time: waits between reconnection attempts
        :type retry_time: int
        :param thread_event: communicate with thread from a signal
        :type thread_event: threading.Event

        :returns: device_proxy (tango.DeviceProxy | None)
        """
        device_proxy = None
        proxy_created = False
        try_count = 1
        while not proxy_created and (thread_event and not thread_event.is_set()):
            try:
                device_proxy = tango.DeviceProxy(trl)
                proxy_created = True
            except tango.DevFailed:
                self._logger.exception(f"An error occured creating a device proxy to {trl}")
                self._logger.debug(
                    f"Try number {try_count}: failed to connect to tango device server"
                    f" {trl}, retrying in {retry_time}s"
                )
                try_count += 1
                if thread_event:
                    thread_event.wait(timeout=retry_time)

        if device_proxy is None:
            self._logger.debug(f"DeviceProxy to {trl} was not created. NoneType returned")
            return device_proxy

        if not self._is_tango_device_running(device_proxy):
            self._wait_for_device(device_proxy, thread_event=thread_event)
        self.device_proxies[trl] = device_proxy
        return device_proxy
