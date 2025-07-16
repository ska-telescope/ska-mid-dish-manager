"""Unit tests for watchdog timer class."""

import time

import pytest

from ska_mid_dish_manager.utils.schedulers import (
    DEFAULT_WATCHDOG_TIMEOUT,
    WatchdogTimer,
    WatchdogTimerInactiveError,
)


class TestWatchdogTimerBase:
    def setup_method(self):
        """Set up context."""
        self.timeout = 2.0
        self.timeout_expire_buffer = 0.2  # buffer to ensure the timer has expired
        self.callback_called = False

        def callback():
            self.callback_called = True

        self.watchdog_timer = WatchdogTimer(callback_on_timeout=callback, timeout=self.timeout)

    def teardown_method(self):
        """Clean up context."""
        self.watchdog_timer.disable()
        assert self.watchdog_timer._timer is None


@pytest.mark.unit
class TestWatchdogTimer(TestWatchdogTimerBase):
    """Tests for WatchdogTimer class."""

    def test_watchdog_inactive_on_init(self):
        """Test that the watchdog timer is inactive on initialization."""
        time.sleep(self.timeout + self.timeout_expire_buffer)
        assert not self.callback_called

    def test_enable(self):
        """Test enabling the watchdog timer."""
        self.watchdog_timer.enable()
        assert not self.callback_called
        time.sleep(self.timeout + self.timeout_expire_buffer)
        assert self.callback_called

    def test_enable_timeout_override(self):
        """Test overriding the watchdog timer timeout."""
        additional_time = 2.0
        # make longer than the default timeout
        override_timeout = self.timeout + additional_time
        self.watchdog_timer.enable(override_timeout)
        assert not self.callback_called
        time.sleep(self.timeout + self.timeout_expire_buffer)
        assert not self.callback_called
        # Let the timer expire
        time.sleep(additional_time + self.timeout_expire_buffer)
        assert self.callback_called

    def test_reset(self):
        """Test resetting the watchdog timer."""
        self.watchdog_timer.enable()
        assert not self.callback_called
        # Test reset multiple times before the timeout
        for _ in range(5):
            time.sleep(self.timeout / 2)
            self.watchdog_timer.reset()

        assert not self.callback_called
        # Let the timer expire
        time.sleep(self.timeout + self.timeout_expire_buffer)
        assert self.callback_called

    def test_disable(self):
        """Test disabling the watchdog timer."""
        self.watchdog_timer.enable()
        assert not self.callback_called
        self.watchdog_timer.disable()
        assert self.watchdog_timer._timer is None
        assert not self.callback_called

    def test_timeout_callback(self):
        """Test that the callback is called after the timeout."""
        self.watchdog_timer.enable()
        # Wait for longer than the timeout to ensure the callback is called
        time.sleep(self.timeout + self.timeout_expire_buffer)
        assert self.callback_called

    def test_init_fails_with_negative_timeout(self):
        """Test that instantiation fails with a negative timeout."""
        with pytest.raises(ValueError, match="Timeout must be greater than 0."):
            WatchdogTimer(timeout=-1.0)

    def test_init_fails_with_zero_timeout(self):
        """Test that instantiation fails with a zero timeout."""
        with pytest.raises(ValueError, match="Timeout must be greater than 0."):
            WatchdogTimer(timeout=0.0)

    def test_enable_timeout_neg_override(self):
        """Test overriding the watchdog timer with negative timeout."""
        with pytest.raises(
            ValueError, match="Watchdog timer is disabled. Timeout must be greater than 0."
        ):
            self.watchdog_timer.enable(-1)
        assert not self.callback_called

    def test_enable_idempotency(self):
        """Test enabling the watchdog timer multiple times."""
        self.watchdog_timer.enable()
        self.watchdog_timer.enable()
        assert not self.callback_called
        time.sleep(self.timeout + self.timeout_expire_buffer)
        assert self.callback_called

    def test_callback_made_once(self):
        """Test that the callback is made only once after the timeout."""
        self.watchdog_timer.enable()
        time.sleep(self.timeout + self.timeout_expire_buffer)
        assert self.callback_called
        # Reset callback_called flag and check again
        self.callback_called = False
        time.sleep(self.timeout + self.timeout_expire_buffer)
        assert not self.callback_called

    def test_reset_without_enable(self):
        """Test that resetting without enabling raises an error."""
        with pytest.raises(
            WatchdogTimerInactiveError, match=r"Watchdog timer is disabled. Call enable first."
        ):
            self.watchdog_timer.reset()


@pytest.mark.unit
class TestWatchdogTimerDefault(TestWatchdogTimerBase):
    """Tests for WatchdogTimer default case."""

    def setup_method(self):
        """Set up context."""
        self.timeout_expire_buffer = 0.2
        self.callback_called = False

        def callback():
            self.callback_called = True

        self.watchdog_timer = WatchdogTimer(callback_on_timeout=callback)

    def test_default_timeout(self):
        """Test that the default timeout is used if not overridden."""
        self.watchdog_timer.enable()
        assert not self.callback_called
        time.sleep(DEFAULT_WATCHDOG_TIMEOUT + self.timeout_expire_buffer)
        assert self.callback_called
