"""Unit tests for DeviceProxyManager class."""

import logging
from threading import Event
from unittest import mock

import pytest
import tango

from ska_mid_dish_manager.component_managers.device_proxy_factory import DeviceProxyManager

LOGGER = logging.getLogger(__name__)


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.device_proxy_factory.tango.DeviceProxy")
class TestDeviceProxyManager:
    """Tests for DeviceProxyManager"""

    def setup_method(self):
        """Set up context"""
        self.signal = Event()
        self.dev_factory = DeviceProxyManager(LOGGER, self.signal)

    def test_only_one_device_proxy_is_created_per_device(self, patch_dp, caplog):
        """Test dp creation."""
        caplog.set_level(logging.DEBUG)

        trl = "some/device/address"

        new_dp_log = f"Creating DeviceProxy to device at {trl}"
        dp = self.dev_factory(trl)
        assert new_dp_log in caplog.text

        existing_dp_log = f"Returning existing DeviceProxy to device at {trl}"
        dp1 = self.dev_factory("some/device/address")
        assert existing_dp_log in caplog.text

        # check that both device proxy instances point to the same object
        assert id(dp) == id(dp1)

    def test_device_proxy_creation_is_retried_in_a_reasonable_manner(self, patch_dp, caplog):
        """Test dp creation retry in event of failure."""
        caplog.set_level(logging.DEBUG)

        patch_dp.side_effect = tango.DevFailed("FAIL")

        trl = "a/b/c"
        self.dev_factory(trl)

        default_retry_times = [1, 2, 3, 4, 6]
        logs = [record.message for record in caplog.records]
        for count, retry_time in enumerate(default_retry_times, start=1):
            assert (
                f"Try number {count}: "
                f"An error occurred creating a device proxy to {trl}, retrying in {retry_time}s"
                in logs
            )

    def test_device_proxy_creation_retry_is_stopped_by_event_signal(self, patch_dp, caplog):
        """Test dp creation and reconnection retry can be cancelled"""
        caplog.set_level(logging.DEBUG)

        trl = "a/device/address"
        self.signal.set()
        dev_proxy = self.dev_factory(trl)

        assert dev_proxy is None
        logs = [record.message for record in caplog.records]
        cancellation_log = "Connection to device cancelled"
        failure_log = f"Failed creating DeviceProxy to device at {trl}"

        assert cancellation_log in logs
        assert failure_log in logs

    def test_device_proxy_is_verified_as_alive_before_returned(self, patch_dp):
        """Test dp is tested before returned to caller."""
        # configure a mock device proxy
        mock_dp = mock.Mock(name="the mock")
        mock_dp_ping = mock.Mock(side_effect=tango.DevFailed("FAIL"))
        mock_dp_reconnect = mock.Mock(side_effect=tango.DevFailed("FAIL"))
        mock_dp.ping = mock_dp_ping
        mock_dp.reconnect = mock_dp_reconnect

        patch_dp.return_value = mock_dp

        trl = "another/device/address"
        self.dev_factory(trl)

        mock_dp_ping.assert_called_once()
        mock_dp_reconnect.assert_called_with(True)
