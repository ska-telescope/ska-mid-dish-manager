"""A factory for creating and managing tango device proxies"""

import logging
import time
from typing import Any

import tango


class DeviceProxyManager:
    """
    Manage CORBA object(s) (tango.DeviceProxy) with a connection to the server

    Too many device proxy objects to the same server is unnecessary and probably
    risky; i.e. any device proxy thread dying can crash the device server process

    Note: The caller should wrap the call in tango.EnsureOmniThread
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.device_proxies = {}

    def __call__(self, trl, thread_event=None) -> Any:
        device_proxy = self.device_proxies.get(trl)

        # import pdb; pdb.set_trace()
        if device_proxy:
            if not self._is_tango_device_running(device_proxy):
                self._wait_for_device(device_proxy)
            return device_proxy

        device_proxy = self.create_tango_device_proxy(trl, thread_event)
        return device_proxy

    def _is_tango_device_running(self, tango_device_proxy):
        """Checks if the TANGO device server is running.

        :param tango_device_proxy: a client to the device server
        :type tango_device_proxy: tango.DeviceProxy

        :returns: is_device_running (boolean)
        """
        try:
            tango_device_proxy.ping()
        except tango.DevFailed:
            self.logger.exception(f"Failed to ping device proxy: {tango_device_proxy.dev_name()}")
            is_device_running = False
        else:
            is_device_running = True

        return is_device_running

    def _wait_for_device(self, tango_device_proxy, retry_time=2):
        """
        Wait until it the client has established a connection with the
        device server and/or for the device server to be up and running.

        :param tango_device_proxy: a client to the device server
        :type tango_device_proxy: tango.DeviceProxy
        :param retry_time: waits between reconnection attempts
        :type retry_time: int

        :returns: is_device_connected (boolean)
        """
        is_device_connected = False
        while not is_device_connected:
            try:
                tango_device_proxy.reconnect(True)
            except tango.DevFailed:
                self.logger.exception(
                    f"Failed to reconnect to device proxy: {tango_device_proxy.dev_name()}"
                )
                self.logger.debug(f"Attempting reconnection to the device proxy in {retry_time}s")
                time.sleep(retry_time)
            else:
                is_device_connected = True

    def create_tango_device_proxy(self, trl, retry_time=2, thread_event=None):
        """
        Wait until it the sub component manager has established a connection
        with the device server and/or for the device server to be up and running.

        :param tango_device_proxy: a client to the device server
        :type tango_device_proxy: tango.DeviceProxy
        :param retry_time: waits between reconnection attempts
        :type retry_time: int

        :returns: is_device_connected (boolean)
        """
        # import pdb; pdb.set_trace()
        proxy_created = False
        try_count = 0
        while not proxy_created:
            try:
                device_proxy = tango.DeviceProxy(trl)
                proxy_created = True
            except tango.DevFailed:
                self.logger.exception(f"An error occured creating a device proxy to {trl}")
                self.logger.debug(
                    f"Try number {try_count}: failed to connect to tango device server {trl}, retrying in {retry_time}s"
                )
                try_count += 1
                if thread_event:
                    thread_event.wait(timeout=retry_time)
                    continue
                time.sleep(retry_time)

        if not self._is_tango_device_running(device_proxy):
            self._wait_for_device(device_proxy)
        self.device_proxies[trl] = device_proxy
        return device_proxy
