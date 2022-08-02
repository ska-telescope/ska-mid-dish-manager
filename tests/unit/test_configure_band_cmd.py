import logging
from unittest.mock import MagicMock, patch

import pytest
import tango
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.dish_manager import DishManager
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
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
    def test_configure_band_cmd_succeeds_when_dish_mode_is_config(
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

        self.spfrx_cm._update_component_state(
            operating_mode=SPFRxOperatingMode.CONFIGURE
        )
        event_store.wait_for_value(DishMode.CONFIG)
        self.ds_cm._update_component_state(configured_band=Band.B2)
        event_store.wait_for_value(Band.B2)

        # Clear out the queue to make sure we don't catch old events
        event_store.clear_queue()

        # Request ConfigureBand2 on SPFRx
        [[_], [unique_id]] = self.device_proxy.ConfigureBand2()
        assert event_store.wait_for_command_id(unique_id)
