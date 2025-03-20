# pylint: disable=protected-access
"""Unit tests checking SPFRx component manager periodically calls MonitorPing."""

import logging
import threading
import time
from unittest import mock

import pytest
from tango import DevFailed

from ska_mid_dish_manager.component_managers.spfrx_cm import MonitorPing, SPFRxComponentManager

LOGGER = logging.getLogger(__name__)


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.device_proxy_factory.tango")
def test_monitor_ping_is_executed_on_spfrx_while_communication_is_sought(patch_tango, caplog):
    """
    Test that the 'MonitorPing' command is executed on the
    SPFRxComponentManager when communication is initiated.
    """
    caplog.set_level(logging.DEBUG)

    state_lock = threading.Lock()
    spfrx_cm = SPFRxComponentManager(
        "a/b/c",
        LOGGER,
        state_lock,
    )

    # set up more mocks
    spfrx_cm._fetch_build_state_information = mock.MagicMock(name="mock_build_state")

    with mock.patch(
        "ska_mid_dish_manager.component_managers.spfrx_cm.MonitorPing._execute_monitor_ping"
    ) as mocked_monitor_ping:
        with mock.patch(
            "ska_mid_dish_manager.component_managers.spfrx_cm.tango.DeviceProxy"
        ) as mocked_dp:
            spfrx_cm.start_communicating()
            assert spfrx_cm._monitor_ping_thread
            assert spfrx_cm._monitor_ping_thread.is_alive()
            assert mocked_monitor_ping.call_count > 0
            spfrx_cm.stop_communicating()
            assert not spfrx_cm._monitor_ping_thread


def test_monitor_ping_runs():
    """Test that MonitorPing is called"""

    with mock.patch("ska_mid_dish_manager.component_managers.spfrx_cm.tango") as mocked_tango:
        mocked_dp = mock.MagicMock()
        mocked_tango.DeviceProxy.return_value = mocked_dp
        mocked_logger = mock.MagicMock()
        stop_event = threading.Event()
        mon_ping_thread = MonitorPing(mocked_logger, 1.0, stop_event, "a/b/c")
        mon_ping_thread.start()
        stop_event.wait(3)

        # check that we can exit the thread
        stop_event.set()
        mon_ping_thread.join()

        assert mocked_tango.DeviceProxy.call_count == 1
        # In 3 seconds it should be called a few times
        assert mocked_dp.command_inout.call_count > 1
        assert mocked_dp.command_inout.call_count < 5


def test_monitor_ping_log_count():
    """Test that MonitorPing logs error only PING_ERROR_LOG_REPEAT times"""

    with mock.patch("ska_mid_dish_manager.component_managers.spfrx_cm.tango") as mocked_tango:
        mocked_dp = mock.MagicMock()
        mocked_dp.command_inout.side_effect = DevFailed()
        mocked_tango.DeviceProxy.return_value = mocked_dp
        mocked_logger = mock.MagicMock()
        stop_event = threading.Event()
        mon_ping_thread = MonitorPing(mocked_logger, 1.0, stop_event, "a/b/c")
        mon_ping_thread.PING_ERROR_LOG_REPEAT = 2
        mon_ping_thread.start()
        stop_event.wait(4)

        # check that we can exit the thread
        stop_event.set()
        mon_ping_thread.join()

        assert mocked_tango.DeviceProxy.call_count == 1
        assert mocked_dp.command_inout.call_count > 2
        assert mocked_logger.exception.call_count == 2
