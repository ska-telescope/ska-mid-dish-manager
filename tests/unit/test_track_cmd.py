"""Unit tests for the Track command."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import tango
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.dish_manager import DishManager
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
        self.dish_manager_cm = class_instance.component_manager

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

        self.dish_manager_cm._update_component_state(
            dish_mode=current_dish_mode
        )
        event_store.wait_for_value(current_dish_mode, timeout=5)
        with pytest.raises(tango.DevFailed):
            _, _ = self.device_proxy.Track()

    def test_set_track_cmd_succeeds_when_dish_mode_is_operate(
        self,
        event_store,
    ):
        attributes_to_subscribe_to = (
            "dishMode",
            "longRunningCommandResult",
            "pointingState",
        )
        for attribute_name in attributes_to_subscribe_to:
            self.device_proxy.subscribe_event(
                attribute_name,
                tango.EventType.CHANGE_EVENT,
                event_store,
            )

        # Force dishManager dishMode to go to OPERATE
        self.ds_cm._update_component_state(operatingmode=DSOperatingMode.POINT)
        self.spf_cm._update_component_state(
            operatingmode=SPFOperatingMode.OPERATE
        )
        self.spfrx_cm._update_component_state(
            operatingmode=SPFRxOperatingMode.DATA_CAPTURE
        )
        event_store.wait_for_value(DishMode.OPERATE)
        self.ds_cm._update_component_state(pointingstate=PointingState.READY)
        event_store.wait_for_value(PointingState.READY)

        # Clear out the queue to make sure we don't catch old events
        event_store.clear_queue()

        # Request Track on Dish
        [[_], [unique_id]] = self.device_proxy.Track()
        assert event_store.wait_for_command_id(unique_id)

        # transition DS pointingState to TRACK
        self.ds_cm._update_component_state(pointingstate=PointingState.SLEW)
        event_store.wait_for_value(PointingState.SLEW)
        assert not self.device_proxy.achievedTargetLock

        self.ds_cm._update_component_state(pointingstate=PointingState.TRACK)
        event_store.wait_for_value(PointingState.TRACK)
        assert self.device_proxy.achievedTargetLock
