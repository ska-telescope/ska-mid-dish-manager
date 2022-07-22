"""Unit tests for setstandby_fp command."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import tango
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.dish_manager import DishManager
from ska_mid_dish_manager.models.dish_enums import DishMode, OperatingMode

LOGGER = logging.getLogger(__name__)


# pylint:disable=attribute-defined-outside-init
# pylint:disable=protected-access
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
            self.tango_context = DeviceTestContext(DishManager)
            self.tango_context.start()

    def test_standb_by_fp(self, event_store):
        """Execute tests"""
        device_proxy = self.tango_context.device

        class_instance = DishManager.instances.get(device_proxy.name())
        ds_cm = class_instance.component_manager.component_managers["DS"]
        spf_cm = class_instance.component_manager.component_managers["SPF"]
        spfrx_cm = class_instance.component_manager.component_managers["SPFRX"]

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

        # Clear out the queue to make sure we don't catch old events
        event_store.clear_queue()

        # transition subservient devices to FP mode and observe that
        # DishManager transitions dishMode to FP mode after all
        # subservient devices are in FP
        ds_cm._update_component_state(operating_mode=OperatingMode.STANDBY_FP)
        assert device_proxy.dishMode == DishMode.STANDBY_LP

        spf_cm._update_component_state(operating_mode=OperatingMode.STANDBY_FP)
        assert device_proxy.dishMode == DishMode.STANDBY_LP

        spfrx_cm._update_component_state(
            operating_mode=OperatingMode.STANDBY_FP
        )
        assert event_store.wait_for_value(DishMode.STANDBY_FP)

    def teardown_method(self):
        """Tear down context"""
        self.tango_context.stop()
