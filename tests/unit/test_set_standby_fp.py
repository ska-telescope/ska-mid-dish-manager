"""Unit tests for setstandby_fp command."""

import logging
from mmap import PROT_WRITE
from unittest.mock import MagicMock, patch

import pytest
import tango
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.dish_manager import DishManager
from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    DSPowerState,
    SPFOperatingMode,
    SPFPowerState,
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
        self.device_proxy = self.tango_context.device
        class_instance = DishManager.instances.get(self.device_proxy.name())
        self.ds_cm = class_instance.component_manager.component_managers["DS"]
        self.spf_cm = class_instance.component_manager.component_managers[
            "SPF"
        ]
        self.spfrx_cm = class_instance.component_manager.component_managers[
            "SPFRX"
        ]
        self.dish_manager_cm = class_instance.component_manager
        # trigger transition to StandbyLP mode to
        # mimic automatic transition after startup
        self.ds_cm._update_component_state(
            operatingmode=DSOperatingMode.STANDBY_LP
        )
        self.spfrx_cm._update_component_state(
            operatingmode=SPFRxOperatingMode.STANDBY
        )
        self.spf_cm._update_component_state(
            operatingmode=SPFOperatingMode.STANDBY_LP
        )

    def teardown_method(self):
        """Tear down context"""
        self.tango_context.stop()

    def test_standb_by_fp(self, event_store):
        """Execute tests"""
        self.device_proxy.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )
        self.device_proxy.subscribe_event(
            "longRunningCommandResult",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )
        assert event_store.wait_for_value(DishMode.STANDBY_LP)
        # Clear out the queue to make sure we don't catch old events
        event_store.clear_queue()

        # Transition DishManager to STANDBY_FP mode
        self.device_proxy.SetStandbyFPMode()

        # transition subservient devices to FP mode and observe that
        # DishManager transitions dishMode to FP mode after all
        # subservient devices are in FP
        self.ds_cm._update_component_state(
            operatingmode=DSOperatingMode.STANDBY_FP
        )
        self.ds_cm._update_component_state(powerstate=DSPowerState.FULL_POWER)
        self.spf_cm._update_component_state(
            operatingmode=SPFOperatingMode.OPERATE
        )
        self.spf_cm._update_component_state(
            powerstate=SPFPowerState.FULL_POWER
        )
        self.spfrx_cm._update_component_state(
            operatingmode=SPFRxOperatingMode.DATA_CAPTURE
        )
        #  we can now expect dishMode to transition to STANDBY_FP
        assert event_store.wait_for_value(DishMode.STANDBY_FP)
