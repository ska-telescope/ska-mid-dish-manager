"""Test the SPFRx component manager's device proxy timeout."""

import logging
import threading
from unittest import mock

import pytest

from ska_mid_dish_manager.component_managers.spfrx_cm import SPFRxComponentManager
from ska_mid_dish_manager.models.constants import SLOW_DEVICE_PROXY_TIMEOUT_MS


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.device_proxy_factory.tango.DeviceProxy")
def test_slow_spfrx_cm_proxy(patched_dp: mock.MagicMock) -> None:
    """Test that the SPFRx device proxy is created with the extended timeout."""
    trl = "a/b/c"
    cm = SPFRxComponentManager(trl, logging.getLogger(), threading.Lock())

    mocked_device_proxy = cm._device_proxy_factory(trl)

    patched_dp.assert_called_once_with(trl)
    assert SLOW_DEVICE_PROXY_TIMEOUT_MS == 12000
    # the slow timeout must be the one left in effect, not the default
    mocked_device_proxy.set_timeout_millis.assert_called_with(12000)
