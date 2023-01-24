"""Unit tests verifying model against DS_SetStowMode transition."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import tango
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.dish_manager import DishManager
from ska_mid_dish_manager.models.dish_enums import DishMode, DSOperatingMode

LOGGER = logging.getLogger(__name__)


# pylint:disable=attribute-defined-outside-init
@pytest.mark.unit
@pytest.mark.forked
class TestStowMode:
    """Tests for SetStowMode"""

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

    def teardown_method(self):
        """Tear down context"""
        self.tango_context.stop()

    # pylint: disable=missing-function-docstring, protected-access
    def test_stow_mode(
        self,
        event_store,
    ):
        device_proxy = self.tango_context.device
        device_proxy.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        class_instance = DishManager.instances.get(device_proxy.name())
        ds_cm = class_instance.component_manager.component_managers["DS"]

        # Pretend DS goes into STOW
        ds_cm._update_component_state(operatingmode=DSOperatingMode.STOW)
        event_store.wait_for_value(DishMode.STOW)

    def test_stow_mode_progress_updates(self, event_store):
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

        # unsubscribe to stop listening for dishMode events
        self.device_proxy.unsubscribe_event(sub_id)
        # Clear out the queue to make sure we dont keep previous events
        event_store.clear_queue()

        # Transition DishManager to STANDBY_FP mode
        [[_], [unique_id]] = self.device_proxy.SetStandbyLPMode()

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

        events = event_store.wait_for_command_id(unique_id, timeout=6)

        events_string = "".join([str(event) for event in events])

        print(events_string)

        expected_progress_updates = [
            "Stow called on DS",
            (
                "Awaiting DS operatingmode to change to "
                "[<DSOperatingMode.STOW: 5>]"
            ),
            "Awaiting dishmode change to 5",
            (
                "DS operatingmode changed to, "
                "[<DSOperatingMode.STOW: 5>]"
            ),
            "SetStowMode completed",
        ]

        for message in expected_progress_updates:
            assert message in events_string
