"""Unit tests for setstandby_lp command."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import tango
from ska_tango_base.commands import ResultCode
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
class TestSetStandByLPMode:
    """Tests for SetStandByLPMode"""

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

    def test_standbylp_cmd_fails_from_standbylp_dish_mode(self, event_store):
        """Execute tests"""
        self.device_proxy.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )
        assert event_store.wait_for_value(DishMode.STANDBY_LP)

        with pytest.raises(tango.DevFailed):
            _, _ = self.device_proxy.SetStandbyLPMode()

    def test_standbylp_cmd_succeeds_from_standbyfp_dish_mode(
        self, event_store
    ):
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

        # Force dishManager dishMode to go to STANDBY-FP
        self.ds_cm._update_component_state(
            operatingmode=DSOperatingMode.STANDBY_FP
        )
        self.spf_cm._update_component_state(
            operatingmode=SPFOperatingMode.OPERATE
        )
        self.spfrx_cm._update_component_state(
            operatingmode=SPFRxOperatingMode.STANDBY
        )
        assert event_store.wait_for_value(DishMode.STANDBY_FP)

        # Transition DishManager to STANDBY_LP issuing a command
        [[result_code], [_]] = self.device_proxy.SetStandbyLPMode()
        assert ResultCode(result_code) == ResultCode.QUEUED

        # Clear out the queue to make sure we don't catch old events
        event_store.clear_queue()

        # transition subservient devices to their respective operatingMode
        # and observe that DishManager transitions dishMode to LP mode. No
        # need to change the component state of SPFRX since it's in the
        # expected operating mode
        self.ds_cm._update_component_state(
            operatingmode=DSOperatingMode.STANDBY_LP
        )

        self.spf_cm._update_component_state(
            operatingmode=SPFOperatingMode.STANDBY_LP
        )
        # we can now expect dishMode to transition to STANDBY_LP
        assert event_store.wait_for_value(DishMode.STANDBY_LP, timeout=6)
