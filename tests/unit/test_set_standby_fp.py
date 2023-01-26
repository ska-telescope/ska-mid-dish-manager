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

        # During sub device command execution, we wait for state changes on our
        # sub devices to work out if the command has completed.
        # We do this both via event updates as well as periodic reads on the
        # sub devices (poll).
        # Since we mock out the tango layer, read_attribute returns a mock
        # object.
        # This then is used to update state which fails.
        self.ds_cm.read_update_component_state = MagicMock()
        self.spf_cm.read_update_component_state = MagicMock()
        self.spfrx_cm.read_update_component_state = MagicMock()

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

    def test_standby_fp(self, event_store_class):
        """Execute tests"""
        dish_mode_event_store = event_store_class()
        progress_event_store = event_store_class()

        self.device_proxy.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            dish_mode_event_store,
        )

        self.device_proxy.subscribe_event(
            "longRunningCommandProgress",
            tango.EventType.CHANGE_EVENT,
            progress_event_store,
        )

        assert dish_mode_event_store.wait_for_value(DishMode.STANDBY_LP)

        self.dish_manager_cm._update_component_state(configuredband=Band.B2)

        # Transition DishManager to STANDBY_FP mode
        self.device_proxy.SetStandbyFPMode()

        # Clear out the queue to make sure we don't catch old events
        dish_mode_event_store.clear_queue()

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
        assert dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP)

        expected_progress_updates = [
            "SetStandbyFPMode called on DS",
            (
                "Awaiting DS operatingmode to change to "
                "[<DSOperatingMode.STANDBY_FP: 3>]"
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

        events = progress_event_store.wait_for_progress_update(
            expected_progress_updates[-1], timeout=6
        )

        events_string = "".join([str(event) for event in events])

        # Check that all the expected progress messages appeared
        # in the event store
        for message in expected_progress_updates:
            assert message in events_string
