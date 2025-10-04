"""A factory for creating and managing tango device proxies."""

import logging
from functools import wraps
from threading import Event
from typing import Any, Callable, Dict

import tango


def retry_connection(func: Callable) -> Any:
    """Return a function that retries connection to a tango device if it is not available.

    This function is intended to be used as a decorator:

    .. code-block:: python

        @retry_connection
        def _create_tango_device_proxy(trl): ...

    :param func: the wrapped function

    :return: the wrapped function
    """

    # pylint: disable=protected-access
    @wraps(func)
    def _wrapper(device_proxy_manager: Any, *args: Any, **kwargs: Any) -> Any:
        """Wrapper function that implements the functionality of the decorator.

        :param device_proxy_manager: an instance of the DeviceProxyManager
        :param args: positional arguments to the wrapped function
        :param kwargs: keyword arguments to the wrapped function

        :raises Tango.DevFailed: if final retry attempt fails
                RunTimeError: if stop communication is invoked
        :return: whatever the wrapped function returns
        """
        max_retries = 5  # threshold after which retry ceases
        retry_time = 1  # initial wait between retry attempts
        back_off = 1.5  # retry_time factor multiplier

        try_count = 1
        while max_retries > 0 and not device_proxy_manager.event_signal.is_set():
            try:
                return func(device_proxy_manager, *args, **kwargs)
            except tango.DevFailed:
                # build up the log message for the specific function
                if "wait" in func.__name__:
                    dev_name = args[0].dev_name()
                    msg = (
                        f"Try number {try_count}: Failed to reconnect to device "
                        f"{dev_name}, retrying connection in {retry_time}s"
                    )
                else:
                    trl = args[0]
                    msg = (
                        f"Try number {try_count}: An error occurred creating a device proxy to "
                        f"{trl}, retrying in {retry_time}s"
                    )

                device_proxy_manager.logger.debug(msg)
                device_proxy_manager.event_signal.wait(retry_time)
                retry_time = round(back_off * retry_time)
                max_retries -= 1
                try_count += 1

        # handle case where stop monitoring is triggered during
        # proxy creation or attempt to reconnect
        if device_proxy_manager.event_signal.is_set():
            device_proxy_manager.logger.debug("Connection to device cancelled")
            raise RuntimeError("Connection interrupted")

        # throw in one more retry attempt, why not :p
        # and allow the error to be raised if an exception occurs
        return func(device_proxy_manager, *args, **kwargs)

    return _wrapper


class DeviceProxyManager:
    """Manage tango.DeviceProxy with a connection to a device.

    Too many device proxy objects to the same device is unnecessary and probably
    risky; i.e. any device proxy thread dying can crash the device server process
    """

    def __init__(
        self, logger: logging.Logger = logging.getLogger(__name__), thread_event: Event = Event()
    ):
        self._device_proxies: Dict[str, tango.DeviceProxy] = {}
        self.logger = logger
        self.event_signal = thread_event

    def __del__(self) -> None:
        """Remove all device proxies when the object is deleted."""
        self.factory_reset()

    def __call__(self, trl: str) -> Any:
        device_proxy = self._device_proxies.get(trl)

        if device_proxy is None:
            self.logger.debug(f"Creating DeviceProxy to device at {trl}")
            try:
                device_proxy = self._create_tango_device_proxy(trl)
            except (tango.DevFailed, RuntimeError):
                self.logger.warning("Failed creating DeviceProxy to device at %s", trl)
                return device_proxy
            self._device_proxies[trl] = device_proxy

        if not self._is_tango_device_running(device_proxy):
            try:
                self.wait_for_device(device_proxy)
            except (tango.DevFailed, RuntimeError):
                self.logger.warning("Device at %s is unresponsive.", trl)

        device_proxy.set_timeout_millis(5000)  # set a 5 second timeout
        return device_proxy

    def _is_tango_device_running(self, tango_device_proxy: tango.DeviceProxy) -> bool:
        """Checks if the TANGO device is running.

        :param tango_device_proxy: a client to the device
        :type tango_device_proxy: tango.DeviceProxy

        :returns: is_device_running (boolean)
        """
        with tango.EnsureOmniThread():
            try:
                tango_device_proxy.ping()
            except tango.DevFailed:
                dev_name = tango_device_proxy.dev_name()
                self.logger.error("Failed to ping device proxy: %s", dev_name)
                is_device_running = False
            else:
                is_device_running = True

        return is_device_running

    @retry_connection
    def wait_for_device(
        self,
        tango_device_proxy: tango.DeviceProxy,
    ) -> None:
        """Wait until it the client has established a connection with
        the device and/or for the device to be up and running.

        :param tango_device_proxy: a client to the device
        :type tango_device_proxy: tango.DeviceProxy

        :returns: None
        """
        with tango.EnsureOmniThread():
            tango_device_proxy.reconnect(True)

    @retry_connection
    def _create_tango_device_proxy(self, trl: str) -> Any:
        """Create and store a device proxy to the device at trl.

        :param trl: the address to the running device
        :type trl: str

        :returns: device_proxy tango.DeviceProxy
        """
        with tango.EnsureOmniThread():
            device_proxy = tango.DeviceProxy(trl)

        return device_proxy

    def factory_reset(self) -> Any:
        """Remove device proxy references to the devices."""
        # delete all references to the device proxies to prevent potential memory leak
        trls = list(self._device_proxies.keys())
        for trl in trls:
            del self._device_proxies[trl]

        # finally, clear any remaining proxies (if any) to ensure memory cleanup
        self._device_proxies.clear()
