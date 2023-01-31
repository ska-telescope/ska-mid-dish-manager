"""Unit tests for setstandbylp command."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import tango
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.dish_manager import DishManager
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

LOGGER = logging.getLogger(__name__)


# pylint:disable=attribute-defined-outside-init
@pytest.mark.unit
@pytest.mark.forked
class TestSetOperateMode:
    """Tests for SetOperateMode"""

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
    def test_set_operate_mode_fails_when_already_in_operate_dish_mode(
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
        spf_cm = class_instance.component_manager.component_managers["SPF"]
        spfrx_cm = class_instance.component_manager.component_managers["SPFRX"]
        # Force dishManager dishMode to go to OPERATE
        ds_cm._update_component_state(operatingmode=DSOperatingMode.POINT)
        spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
        spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.DATA_CAPTURE)
        event_store.wait_for_value(DishMode.OPERATE)

        with pytest.raises(tango.DevFailed):
            # Transition DishManager to OPERATE issuing a command
            _, _ = device_proxy.SetOperateMode()
            assert device_proxy.pointingState == PointingState.UNKNOWN

    def test_set_operate_mode_succeeds_from_standbyfp_dish_mode(
        self,
        event_store_class,
    ):
        main_event_store = event_store_class()
        progress_event_store = event_store_class()

        device_proxy = self.tango_context.device
        for attr in [
            "dishMode",
            "longRunningCommandResult",
            "pointingState",
            "configuredBand",
        ]:
            device_proxy.subscribe_event(
                attr,
                tango.EventType.CHANGE_EVENT,
                main_event_store,
            )

        device_proxy.subscribe_event(
            "longRunningCommandProgress",
            tango.EventType.CHANGE_EVENT,
            progress_event_store,
        )

        class_instance = DishManager.instances.get(device_proxy.name())
        ds_cm = class_instance.component_manager.component_managers["DS"]
        spf_cm = class_instance.component_manager.component_managers["SPF"]
        spfrx_cm = class_instance.component_manager.component_managers["SPFRX"]

        ds_cm.read_update_component_state = MagicMock()
        spf_cm.read_update_component_state = MagicMock()
        spfrx_cm.read_update_component_state = MagicMock()

        # Force dishManager dishMode to go to STANDBY_FP
        ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_FP)
        spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
        spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.STANDBY)
        main_event_store.wait_for_value(DishMode.STANDBY_FP)

        # Clear out the queue to make sure we don't catch old events
        main_event_store.clear_queue()

        # Transition DishManager to OPERATE mode
        # configuredBand not set
        with pytest.raises(tango.DevFailed):
            device_proxy.SetOperateMode()

        # Set configuredBand and try again
        ds_cm._update_component_state(indexerposition=IndexerPosition.B1)
        spf_cm._update_component_state(bandinfocus=BandInFocus.B1)
        spfrx_cm._update_component_state(configuredband=Band.B1)
        main_event_store.wait_for_value(Band.B1)

        device_proxy.SetOperateMode()

        # transition subservient devices to their respective operatingMode
        # and observe that DishManager transitions dishMode to OPERATE mode
        # SPF are already in the expected operatingMode
        ds_cm._update_component_state(operatingmode=DSOperatingMode.POINT)
        spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.DATA_CAPTURE)
        # we can now expect dishMode to transition to OPERATE
        main_event_store.wait_for_value(DishMode.OPERATE)
        ds_cm._update_component_state(pointingstate=PointingState.READY)
        main_event_store.wait_for_value(PointingState.READY)

        expected_progress_updates = [
            "SetPointMode called on DS",
            ("Awaiting DS operatingmode to change to [<DSOperatingMode.POINT: 7>]"),
            "SetOperateMode called on SPF",
            ("Awaiting SPF operatingmode to change to [<SPFOperatingMode.OPERATE: 3>]"),
            "CaptureData called on SPFRX",
            (
                "Awaiting SPFRX operatingmode to change to "
                "[<SPFRxOperatingMode.DATA_CAPTURE: 3>]"
            ),
            "Awaiting dishmode change to 7",
            ("DS operatingmode changed to, [<DSOperatingMode.POINT: 7>]"),
            ("SPF operatingmode changed to, [<SPFOperatingMode.OPERATE: 3>]"),
            ("SPFRX operatingmode changed to, [<SPFRxOperatingMode.DATA_CAPTURE: 3>]"),
            "SetOperateMode completed",
        ]

        events = progress_event_store.wait_for_progress_update(
            expected_progress_updates[-1], timeout=6
        )

        events_string = "".join([str(event) for event in events])

        # Check that all the expected progress messages appeared
        # in the event store
        for message in expected_progress_updates:
            assert message in events_string
