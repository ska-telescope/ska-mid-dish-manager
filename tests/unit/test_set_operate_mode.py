"""Unit tests for setstandbylp command."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import tango
from ska_control_model import CommunicationStatus
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.DishManagerDS import DishManager
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    BandInFocus,
    DishMode,
    DSOperatingMode,
    IndexerPosition,
    PointingState,
    SPFOperatingMode,
    SPFRxOperatingMode,
)
from tests.utils import EventStore

LOGGER = logging.getLogger(__name__)


# pylint:disable=attribute-defined-outside-init
@pytest.mark.unit
@pytest.mark.forked
class TestSetOperateMode:
    """Tests for SetOperateMode"""

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

            for com_man in class_instance.component_manager.sub_component_managers.values():
                com_man._update_communication_state(
                    communication_state=CommunicationStatus.ESTABLISHED
                )

            self.ds_cm.update_state_from_monitored_attributes = MagicMock()
            self.spfrx_cm.update_state_from_monitored_attributes = MagicMock()
            self.spf_cm.update_state_from_monitored_attributes = MagicMock()
            self.spf_cm.write_attribute_value = MagicMock()

            # Wait for the threads to start otherwise the mocks get
            # returned back to non mock
            event_store = EventStore()
            for conn_attr in ["spfConnectionState", "spfrxConnectionState", "dsConnectionState"]:
                self.device_proxy.subscribe_event(
                    conn_attr,
                    tango.EventType.CHANGE_EVENT,
                    event_store,
                )
                event_store.wait_for_value(CommunicationStatus.ESTABLISHED)

    def teardown_method(self):
        """Tear down context"""
        return

    # pylint: disable=missing-function-docstring, protected-access
    def test_set_operate_mode_fails_when_already_in_operate_dish_mode(
        self,
        event_store_class,
    ):
        dish_mode_event_store = event_store_class()
        lrc_status_event_store = event_store_class()

        self.device_proxy.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            dish_mode_event_store,
        )

        self.device_proxy.subscribe_event(
            "longRunningCommandStatus",
            tango.EventType.CHANGE_EVENT,
            lrc_status_event_store,
        )

        # Force dishManager dishMode to go to OPERATE
        self.ds_cm._update_component_state(operatingmode=DSOperatingMode.POINT)
        self.spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
        self.spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.DATA_CAPTURE)
        dish_mode_event_store.wait_for_value(DishMode.OPERATE)

        [[_], [unique_id]] = self.device_proxy.SetOperateMode()
        lrc_status_event_store.wait_for_value((unique_id, "REJECTED"))

    def test_set_operate_mode_succeeds_from_standbyfp_dish_mode(
        self,
        event_store_class,
    ):
        main_event_store = event_store_class()
        progress_event_store = event_store_class()
        result_event_store = event_store_class()

        for attr in [
            "dishMode",
            "pointingState",
            "configuredBand",
        ]:
            self.device_proxy.subscribe_event(
                attr,
                tango.EventType.CHANGE_EVENT,
                main_event_store,
            )

        self.device_proxy.subscribe_event(
            "longRunningCommandProgress",
            tango.EventType.CHANGE_EVENT,
            progress_event_store,
        )

        self.device_proxy.subscribe_event(
            "longRunningCommandResult",
            tango.EventType.CHANGE_EVENT,
            result_event_store,
        )

        # Force dishManager dishMode to go to STANDBY_FP
        self.ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_FP)
        self.spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
        self.spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.STANDBY)
        main_event_store.wait_for_value(DishMode.STANDBY_FP)

        # Transition DishManager to OPERATE mode
        # configuredBand not set
        [[_], [unique_id]] = self.device_proxy.SetOperateMode()
        result_event_store.wait_for_command_result(unique_id, '"Command not allowed"')

        # Set configuredBand and try again
        self.ds_cm._update_component_state(indexerposition=IndexerPosition.B1)
        self.spf_cm._update_component_state(bandinfocus=BandInFocus.B1)
        self.spfrx_cm._update_component_state(configuredband=Band.B1)
        # spfrx operating mode transitions to Data Capture after successful band configuration
        self.spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.DATA_CAPTURE)
        main_event_store.wait_for_value(Band.B1)

        self.device_proxy.SetOperateMode()
        # transition subservient devices to their respective operatingMode
        # and observe that DishManager transitions dishMode to OPERATE mode
        # SPF are already in the expected operatingMode
        self.ds_cm._update_component_state(operatingmode=DSOperatingMode.POINT)
        main_event_store.wait_for_value(DishMode.OPERATE)
        self.ds_cm._update_component_state(pointingstate=PointingState.READY)
        main_event_store.wait_for_value(PointingState.READY)

        expected_progress_updates = [
            "SetPointMode called on DS",
            "SetOperateMode called on SPF",
            "Awaiting dishMode change to OPERATE",
            "SetOperateMode completed",
        ]

        events = progress_event_store.wait_for_progress_update(
            expected_progress_updates[-1], timeout=10
        )

        events_string = "".join([str(event.attr_value.value) for event in events])

        # Check that all the expected progress messages appeared
        # in the event store
        for message in expected_progress_updates:
            assert message in events_string
