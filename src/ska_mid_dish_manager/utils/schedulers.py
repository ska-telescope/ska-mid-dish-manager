"""This module provides functionality related to scheduling and managing of tasks."""

import threading
from typing import Callable

DEFAULT_WATCHDOG_TIMEOUT = 10.0  # seconds


class WatchdogTimerInactiveError(RuntimeError):
    """Exception raised when the watchdog timer is not enabled."""


class WatchdogTimer:
    def __init__(
        self, callback_on_timeout: Callable = None, timeout: float = DEFAULT_WATCHDOG_TIMEOUT
    ):
        """This class implements a watchdog timer that will make a callback
        when the timer expires.

        :param callback_on_timeout: The callback function to be invoked when the timer expires.
        :param timeout: The default time in seconds after which the callback will be
            invoked if not reset, defaults to DEFAULT_WATCHDOG_TIMEOUT
        :raises ValueError: If timeout specified is less than zero.
        """
        if timeout <= 0:
            raise ValueError("Timeout must be greater than 0.")

        self._timeout = timeout
        self._external_callback = callback_on_timeout
        self._timer = None
        self._lock = threading.RLock()
        self._enabled = False

    def enable(self, timeout: float = None):
        """Enable the watchdog timer.

        :param timeout: Time in seconds, defaults to None
        :raises ValueError: If the timeout is less than or equal to zero.
        """
        with self._lock:
            # override the default timeout if provided
            if timeout is not None:
                if timeout <= 0:
                    raise ValueError("Watchdog timer is disabled. Timeout must be greater than 0.")
                self._timeout = timeout

            self._enabled = True
            self._start_timer()

    def is_enabled(self) -> bool:
        """Check if the watchdog timer is enabled."""
        with self._lock:
            return self._enabled

    def disable(self):
        """Disable the watchdog timer."""
        with self._lock:
            self._enabled = False
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def reset(self):
        """Reset the watchdog timer.

        This method will cancel the current timer and start a new one with the
        same timeout. If the timer is not active, it raises an exception.
        :raises WatchdogTimerInactiveError: If called when the timer is disabled / not active.
        """
        with self._lock:
            if not self._enabled:
                raise WatchdogTimerInactiveError("Watchdog timer is disabled. Call enable first.")

            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

            self._start_timer()

    def _start_timer(self):
        """Start the timer.

        If the timer is already running, there is no effect.
        This method should be called with the lock held.
        """
        if self._timer is None and self._enabled:
            self._timer = threading.Timer(self._timeout, self._callback_on_timeout_and_disable)
            self._timer.start()

    def _callback_on_timeout_and_disable(self):
        """Wrapper for the callback to disable the timer after timeout."""
        # Clear the timer reference and disable the watchdog
        with self._lock:
            self._timer = None
            self._enabled = False
        if self._external_callback:
            self._external_callback()
