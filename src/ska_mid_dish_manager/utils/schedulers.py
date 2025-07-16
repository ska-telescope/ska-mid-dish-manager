"""This module provides functionality related to scheduling and managing of tasks."""

import threading

from typing import Callable


class WatchdogTimer:
    def __init__(self, timeout: float, callback_on_timeout: Callable):
        """This class implements a watchdog timer that will make a callback
        when the timer expires.

        :param timeout: The default time in seconds after which the callback will be
        invoked if not reset.
        :type timeout: float
        :param callback_on_timeout: The callback function to be invoked when the timer expires.
        :type callback_on_timeout: Callable
        """
        if timeout <= 0:
            raise ValueError("Timeout must be greater than 0.")

        self._timeout = timeout
        self.callback_on_timeout = callback_on_timeout
        self._timer = None
        self._lock = threading.RLock()
        self._enabled = False

    def enable(self, timeout: float = None):
        """Enable the watchdog timer.

        :param timeout: Time in seconds, defaults to None
        :type timeout: float, optional
        :raises ValueError: If the timeout is less than or equal to zero.
        """
        with self._lock:
            # override the default timeout if provided
            if timeout is not None:
                if timeout <= 0:
                    raise ValueError("Watchdog timer is disabled. Timeout must be greater than 0.")
                self._timeout = timeout
            # handle idempotency
            if not self._enabled:
                self._enabled = True
                self.reset()

    def disable(self):
        """Disable the watchdog timer."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
                self._enabled = False

    def reset(self):
        """Reset the watchdog timer.

        :raises RuntimeError: If called when the timer is not enabled.
        """
        with self._lock:
            if not self._enabled:
                raise RuntimeError("Watchdog timer is not enabled. Call enable() first.")
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._timeout, self.callback_on_timeout)
            self._timer.start()
