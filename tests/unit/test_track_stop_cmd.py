"""Unit tests for the TrackStop command."""

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
class TestTrackStop:
    """Tests for TrackStop"""

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

            for com_man in class_instance.component_manager.sub_component_managers.values():
                com_man._update_communication_state(
                    communication_state=CommunicationStatus.ESTABLISHED
                )

            self.ds_cm = class_instance.component_manager.sub_component_managers["DS"]
            self.spf_cm = class_instance.component_manager.sub_component_managers["SPF"]
            self.spfrx_cm = class_instance.component_manager.sub_component_managers["SPFRX"]
            self.dish_manager_cm = class_instance.component_manager

            self.ds_cm.update_state_from_monitored_attributes = MagicMock()
            self.spf_cm.update_state_from_monitored_attributes = MagicMock()
            self.spfrx_cm.update_state_from_monitored_attributes = MagicMock()

    def teardown_method(self):
        """Tear down context"""
        return

    # pylint: disable=missing-function-docstring, protected-access
    @pytest.mark.parametrize(
        "current_pointing_state",
        [
            PointingState.READY,
            PointingState.SLEW,
            PointingState.SCAN,
        ],
    )
    def test_track_stop_cmd_fails_when_pointing_state_is_not_track(
        self,
        event_store_class,
        current_pointing_state,
    ):
        pointing_state_event_store = event_store_class()
        lrc_status_event_store = event_store_class()

        self.device_proxy.subscribe_event(
            "pointingState",
            tango.EventType.CHANGE_EVENT,
            pointing_state_event_store,
        )

        self.device_proxy.subscribe_event(
            "longRunningCommandStatus",
            tango.EventType.CHANGE_EVENT,
            lrc_status_event_store,
        )

        self.ds_cm._update_component_state(pointingstate=current_pointing_state)
        pointing_state_event_store.wait_for_value(current_pointing_state, timeout=5)

        [[_], [unique_id]] = self.device_proxy.TrackStop()
        lrc_status_event_store.wait_for_value((unique_id, "REJECTED"))

    def test_track_stop_cmd_succeeds_when_pointing_state_is_track(
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
        [[_], [unique_id]] = self.device_proxy.Track()

        # transition DS pointingState to TRACK
        self.ds_cm._update_component_state(pointingstate=PointingState.SLEW)
        main_event_store.wait_for_value(PointingState.SLEW)

        self.ds_cm._update_component_state(pointingstate=PointingState.TRACK)
        main_event_store.wait_for_value(PointingState.TRACK)

        main_event_store.wait_for_command_id(unique_id, timeout=6)

        # Request TrackStop on Dish
        self.device_proxy.TrackStop()

        # transition DS pointingState to READY
        self.ds_cm._update_component_state(pointingstate=PointingState.READY)
        main_event_store.wait_for_value(PointingState.READY)

        expected_progress_updates = [
            "TrackStop called on DS, ID",
            "Awaiting DS pointingstate change to [<PointingState.READY: 0>]",
            "TrackStop completed",
        ]

        events = progress_event_store.wait_for_progress_update(
            expected_progress_updates[-1], timeout=6
        )

        events_string = "".join([str(event) for event in events])

        # Check that all the expected progress messages appeared
        # in the event store
        for message in expected_progress_updates:
            assert message in events_string
