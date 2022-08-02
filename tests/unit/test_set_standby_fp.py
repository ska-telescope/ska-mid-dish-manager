"""Unit tests for setstandby_fp command."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import tango
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.dish_manager import DishManager
from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    SPFOperatingMode,
    SPFRxOperatingMode,
)

LOGGER = logging.getLogger(__name__)


# pylint:disable=attribute-defined-outside-init
# pylint:disable=protected-access
@pytest.mark.unit
@pytest.mark.forked
class TestSetStandByFPMode:
    """Tests for SetStandByFPMode"""

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

        # Clear out the queue to make sure we don't catch old events
        event_store.clear_queue()

        # Transition DishManager to STANDBY_FP mode
        [[_], [unique_id]] = device_proxy.SetStandbyFPMode()
        assert event_store.wait_for_command_id(unique_id)

        # transition subservient devices to FP mode and observe that
        # DishManager transitions dishMode to FP mode after all
        # subservient devices are in FP
        ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_FP)
        assert device_proxy.dishMode == DishMode.STANDBY_LP

        spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
        assert device_proxy.dishMode == DishMode.STANDBY_LP

        spfrx_cm._update_component_state(
            operatingmode=SPFRxOperatingMode.DATA_CAPTURE
        )
        #  we can now expect dishMode to transition to STANDBY_FP
        assert event_store.wait_for_value(DishMode.STANDBY_FP)
