"""Unit tests for setstandby_fp command."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import tango
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.dish_manager import DishManager
from ska_mid_dish_manager.models.dish_enums import (
    Band,
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

    def test_standby_fp(self, event_store):
        """Execute tests"""
        self.device_proxy.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        assert event_store.wait_for_value(DishMode.STANDBY_LP)
        # Clear out the queue to make sure we don't catch old events
        event_store.clear_queue()

        self.dish_manager_cm._update_component_state(configuredband=Band.B2)

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

    def test_standby_fp_progress_updates(self, event_store):
        """Execute tests"""
        self.device_proxy.subscribe_event(
            "longRunningCommandProgress",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        # Subscribe to longRunningCommandResult so that we can see when the
        # function has completed with wait_for_command_id
        self.device_proxy.subscribe_event(
            "longRunningCommandResult",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        sub_id = self.device_proxy.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )
        assert event_store.wait_for_value(DishMode.STANDBY_LP, timeout=6)
        # unsubscribe to stop listening for dishMode events
        self.device_proxy.unsubscribe_event(sub_id)
        # Clear out the queue to make sure we dont keep previous events
        event_store.clear_queue()

        self.dish_manager_cm._update_component_state(configuredband=Band.B2)

        # Transition DishManager to STANDBY_FP mode
        [[_], [unique_id]] = self.device_proxy.SetStandbyFPMode()

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

        events = event_store.wait_for_command_id(unique_id, timeout=6)

        events_string = "".join([str(event) for event in events])

        expected_progress_updates = [
            "SetStandbyFPMode called on DS",
            (
                "Awaiting DS operatingmode to change to "
                "[<DSOperatingMode.STANDBY_LP: 2>]"
            ),
            "SetOperateMode called on SPF",
            (
                "Awaiting SPF operatingmode to change to "
                "[<SPFOperatingMode.OPERATE: 3>]"
            ),
            "CaptureData called on SPFRX",
            (
                "Awaiting SPFRX operatingmode to change to "
                "[<SPFRxOperatingMode.STANDBY: 2>, "
                "<SPFRxOperatingMode.DATA_CAPTURE: 3>]"
            ),
            "Awaiting dishmode change to 3",
            (
                "SPF operatingmode changed to, "
                "[<SPFOperatingMode.OPERATE: 3>]"
            ),
            (
                "SPFRX operatingmode changed to, "
                "[<SPFRxOperatingMode.STANDBY: 2>, "
                "<SPFRxOperatingMode.DATA_CAPTURE: 3>]"
            ),
            "SetStandbyFPMode completed",
        ]

        for message in expected_progress_updates:
            assert message in events_string
