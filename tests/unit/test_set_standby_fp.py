"""Unit tests for setstandby_fp command."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import tango
from ska_control_model import CommunicationStatus
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.DishManagerDS import DishManager
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
            (
                "ska_mid_dish_manager.component_managers.tango_device_cm."
                "TangoDeviceComponentManager.start_communicating"
            )
        ):
            self.tango_context = DeviceTestContext(DishManager)
            self.tango_context.start()
            self.device_proxy = self.tango_context.device
            class_instance = DishManager.instances.get(self.device_proxy.name())
            self.ds_cm = class_instance.component_manager.sub_component_managers["DS"]
            self.spf_cm = class_instance.component_manager.sub_component_managers["SPF"]
            self.spfrx_cm = class_instance.component_manager.sub_component_managers["SPFRX"]
            self.dish_manager_cm = class_instance.component_manager

            class_instance = DishManager.instances.get(self.device_proxy.name())
            for com_man in class_instance.component_manager.sub_component_managers.values():
                com_man._update_communication_state(
                    communication_state=CommunicationStatus.ESTABLISHED
                )

            self.ds_cm.update_state_from_monitored_attributes = MagicMock()
            self.spf_cm.update_state_from_monitored_attributes = MagicMock()
            self.spfrx_cm.update_state_from_monitored_attributes = MagicMock()

            # trigger transition to StandbyLP mode to
            # mimic automatic transition after startup
            self.ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_LP)
            self.spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.STANDBY)
            self.spf_cm._update_component_state(operatingmode=SPFOperatingMode.STANDBY_LP)

    def teardown_method(self):
        """Tear down context"""
        return

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

        # Transition DishManager to STANDBY_FP mode
        self.device_proxy.SetStandbyFPMode()

        # Clear out the queue to make sure we don't catch old events
        dish_mode_event_store.clear_queue()

        # transition subservient devices to FP mode and observe that
        # DishManager transitions dishMode to FP mode after all
        # subservient devices are in FP
        self.ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_FP)
        self.ds_cm._update_component_state(powerstate=DSPowerState.FULL_POWER)
        self.spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
        self.spf_cm._update_component_state(powerstate=SPFPowerState.FULL_POWER)
        #  we can now expect dishMode to transition to STANDBY_FP
        assert dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP)

        expected_progress_updates = [
            "SetStandbyFPMode called on DS",
            "SetOperateMode called on SPF",
            "Awaiting dishMode change to STANDBY_FP",
            "SetStandbyFPMode completed",
        ]

        events = progress_event_store.wait_for_progress_update(
            expected_progress_updates[-1], timeout=6
        )

        events_string = "".join([str(event.attr_value.value) for event in events])

        # Check that all the expected progress messages appeared
        # in the event store
        for message in expected_progress_updates:
            assert message in events_string
