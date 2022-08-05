"""Unit tests for the ConfigureBand2 command on dish manager."""
import logging
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import tango
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.dish_manager import DishManager
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
    DSOperatingMode,
    SPFOperatingMode,
    SPFRxOperatingMode,
)

LOGGER = logging.getLogger(__name__)


# pylint:disable=attribute-defined-outside-init
# pylint:disable=protected-access
@pytest.mark.unit
@pytest.mark.forked
class TestConfigureBand2:
    """Tests for ConfigureBand2"""

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

    def test_configure_band_cmd_succeeds_when_dish_mode_is_standbyfp(
        self,
        event_store,
    ):
        """Test ConfigureBand"""
        attributes_to_subscribe_to = (
            "dishMode",
            "longRunningCommandResult",
            "configuredBand",
        )
        for attribute_name in attributes_to_subscribe_to:
            self.device_proxy.subscribe_event(
                attribute_name,
                tango.EventType.CHANGE_EVENT,
                event_store,
            )
        assert event_store.wait_for_value(DishMode.STANDBY_LP)

        # Clear out the queue to make sure we don't catch old events
        event_store.clear_queue()

        [[_], [unique_id]] = self.device_proxy.SetStandbyFPMode()
        assert event_store.wait_for_command_id(unique_id)

        self.ds_cm._update_component_state(
            operatingmode=int(DSOperatingMode.STANDBY_FP)
        )
        self.spf_cm._update_component_state(
            operatingmode=int(SPFOperatingMode.OPERATE)
        )
        self.spfrx_cm._update_component_state(
            operatingmode=int(SPFRxOperatingMode.DATA_CAPTURE)
        )
        #  we can now expect dishMode to transition to STANDBY_FP
        assert event_store.wait_for_value(DishMode.STANDBY_FP)

        # Request ConfigureBand2 on Dish manager
        future_time = datetime.utcnow() + timedelta(days=1)
        [[_], [unique_id]] = self.device_proxy.ConfigureBand2(
            future_time.isoformat()
        )
        assert event_store.wait_for_command_id(unique_id)

        self.spfrx_cm._update_component_state(configuredband=int(Band.B2))
        event_store.wait_for_value(Band.B2)

        assert self.device_proxy.configuredBand == Band.B2