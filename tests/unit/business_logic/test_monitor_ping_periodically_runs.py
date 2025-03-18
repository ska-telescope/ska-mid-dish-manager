# pylint: disable=protected-access
"""Unit tests checking generic component manager behaviour."""

import logging
import threading
import time
from unittest import mock

import pytest

from ska_mid_dish_manager.component_managers.spfrx_cm import SPFRxComponentManager

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
    spfrx_cm.execute_command = mock.MagicMock(name="mock_exec_command")

    spfrx_cm.start_communicating()
    timer_interval = 3
    time.sleep(timer_interval * 2)

    # the command should have been called more than once in the interval period
    assert spfrx_cm.execute_command.call_count >= 2
    assert spfrx_cm.execute_command.call_args_list[0].args == ("MonitorPing", None)

    spfrx_cm.execute_command.reset_mock()
    spfrx_cm.stop_communicating()
    assert spfrx_cm.execute_command.call_count == 0
