"""Unit tests for the Track command."""

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
    PointingState,
    SPFOperatingMode,
    SPFRxOperatingMode,
)

LOGGER = logging.getLogger(__name__)


# pylint:disable=attribute-defined-outside-init
@pytest.mark.unit
@pytest.mark.forked
class TestTrack:
    """Tests for Track"""

    # pylint: disable=protected-access
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

            for com_man in class_instance.component_manager.sub_component_managers.values():
                com_man._update_communication_state(
                    communication_state=CommunicationStatus.ESTABLISHED
                )

            self.ds_cm.update_state_from_monitored_attributes = MagicMock()
            self.spf_cm.update_state_from_monitored_attributes = MagicMock()
            self.spfrx_cm.update_state_from_monitored_attributes = MagicMock()

    def teardown_method(self):
        """Tear down context"""
        self.tango_context.stop()

    # pylint: disable=missing-function-docstring, protected-access
    @pytest.mark.parametrize(
        "current_dish_mode",
        [
            DishMode.STANDBY_LP,
            DishMode.STANDBY_FP,
            DishMode.STARTUP,
            DishMode.SHUTDOWN,
            DishMode.MAINTENANCE,
            DishMode.STOW,
            DishMode.CONFIG,
        ],
    )
    def test_set_track_cmd_fails_when_dish_mode_is_not_operate(
        self,
        event_store,
        current_dish_mode,
    ):
        self.device_proxy.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        self.dish_manager_cm._update_component_state(dishmode=current_dish_mode)
        event_store.wait_for_value(current_dish_mode, timeout=5)
        with pytest.raises(tango.DevFailed):
            _, _ = self.device_proxy.Track()

    def test_set_track_cmd_succeeds_when_dish_mode_is_operate(
        self,
        event_store_class,
    ):
        main_event_store = event_store_class()
        progress_event_store = event_store_class()

        attributes_to_subscribe_to = (
            "dishMode",
            "longRunningCommandResult",
            "pointingState",
        )
        for attribute_name in attributes_to_subscribe_to:
            self.device_proxy.subscribe_event(
                attribute_name,
                tango.EventType.CHANGE_EVENT,
                main_event_store,
            )

        self.device_proxy.subscribe_event(
            "longRunningCommandProgress",
            tango.EventType.CHANGE_EVENT,
            progress_event_store,
        )

        # Force dishManager dishMode to go to OPERATE
        self.ds_cm._update_component_state(operatingmode=DSOperatingMode.POINT)
        self.spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
        self.spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.DATA_CAPTURE)
        main_event_store.wait_for_value(DishMode.OPERATE)
        self.ds_cm._update_component_state(pointingstate=PointingState.READY)
        main_event_store.wait_for_value(PointingState.READY)

        # Clear out the queue to make sure we don't catch old events
        main_event_store.clear_queue()

        # Request Track on Dish
        self.device_proxy.Track()

        # transition DS pointingState to TRACK
        self.ds_cm._update_component_state(pointingstate=PointingState.SLEW)
        main_event_store.wait_for_value(PointingState.SLEW)

        self.ds_cm._update_component_state(pointingstate=PointingState.TRACK)
        main_event_store.wait_for_value(PointingState.TRACK)

        expected_progress_updates = [
            "Track called on DS, ID",
            "Awaiting pointingstate change to TRACK",
            "Track completed",
        ]

        events = progress_event_store.wait_for_progress_update(
            expected_progress_updates[-1], timeout=6
        )

        events_string = "".join([str(event) for event in events])

        # Check that all the expected progress messages appeared
        # in the event store
        for message in expected_progress_updates:
            assert message in events_string
