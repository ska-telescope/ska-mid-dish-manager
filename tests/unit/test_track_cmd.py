"""Unit tests for setstandbylp command."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import tango
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.dish_manager import DishManager
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

    def teardown_method(self):
        """Tear down context"""
        self.tango_context.stop()

    # pylint: disable=missing-function-docstring, protected-access
    def test_set_track_cmd_fails_when_dish_mode_is_not_operate(
        self,
        event_store,
    ):
        self.device_proxy.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        event_store.wait_for_value(DishMode.STANDBY_LP)
        with pytest.raises(tango.DevFailed):
            _, _ = self.device_proxy.Track()

    def test_set_track_cmd_succeeds_when_dish_mode_is_operate(
        self,
        event_store,
    ):
        attributes_to_subscribe_to = (
            "dishMode",
            "longRunningCommnadResult",
            "pointingState",
        )
        for attribute_name in attributes_to_subscribe_to:
            self.device_proxy.subscribe_event(
                attribute_name,
                tango.EventType.CHANGE_EVENT,
                event_store,
            )

        # Force dishManager dishMode to go to OPERATE
        self.ds_cm._update_component_state(
            operating_mode=DSOperatingMode.POINT
        )
        self.spf_cm._update_component_state(
            operating_mode=SPFOperatingMode.OPERATE
        )
        self.spfrx_cm._update_component_state(
            operating_mode=SPFRxOperatingMode.DATA_CAPTURE
        )
        event_store.wait_for_value(DishMode.OPERATE)

        # Clear out the queue to make sure we don't catch old events
        event_store.clear_queue()

        # Request Track on Dish
        [[_], [unique_id]] = self.device_proxy.Track()
        assert event_store.wait_for_command_result(
            unique_id, '"Track command queued on ds"'
        )

        # transition DS pointingState to TRACK
        self.ds_cm._update_component_state(pointing_state=PointingState.SLEW)
        event_store.wait_for_value(PointingState.SLEW)
        assert not self.device_proxy.achievedTargetLock

        self.ds_cm._update_component_state(pointing_state=PointingState.TRACK)
        event_store.wait_for_value(PointingState.TRACK)
        assert self.device_proxy.achievedTargetLock
