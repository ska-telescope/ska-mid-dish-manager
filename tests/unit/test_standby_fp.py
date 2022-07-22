"""Unit tests for setstandby_fp command."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import tango
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.dish_manager import DishManager
from ska_mid_dish_manager.models.dish_enums import DishMode

LOGGER = logging.getLogger(__name__)


# pylint:disable=attribute-defined-outside-init
@pytest.mark.unit
@pytest.mark.forked
class TestStandByFPMode:
    """Tests for TestStandByFPMode"""

    def setup_method(self):
        """Set up context"""
        with patch(
            "ska_mid_dish_manager.component_managers.tango_device_cm.tango"
        ) as patched_tango:
            patched_dp = MagicMock()
            patched_dp.command_inout = MagicMock()
            patched_tango.DeviceProxy = MagicMock(return_value=patched_dp)
            self.tango_context = DeviceTestContext(DishManager, process=True)
            self.tango_context.start()

    def test_standb_by_fp(self, event_store):
        """Execute tests"""
        device_proxy = self.tango_context.device
        assert device_proxy.ping()
        device_proxy.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )
        device_proxy.subscribe_event(
            "longRunningCommandResult",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )
        assert event_store.wait_for_value(DishMode.STANDBY_LP)
        [[_], [command_id]] = device_proxy.SetStandbyFPMode()
        assert event_store.wait_for_command_result(
            command_id, '"SetStandbyFPMode queued on ds, spf and spfrx"'
        )

    def teardown_method(self):
        """Tear down context"""
        self.tango_context.stop()
