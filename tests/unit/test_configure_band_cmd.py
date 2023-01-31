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
    BandInFocus,
    DishMode,
    DSOperatingMode,
    IndexerPosition,
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
        self.spf_cm = class_instance.component_manager.component_managers["SPF"]
        self.spfrx_cm = class_instance.component_manager.component_managers["SPFRX"]

        self.ds_cm.read_update_component_state = MagicMock()
        self.spf_cm.read_update_component_state = MagicMock()
        self.spfrx_cm.read_update_component_state = MagicMock()

        self.dish_manager_cm = class_instance.component_manager

        # trigger transition to StandbyLP mode to
        # mimic automatic transition after startup
        self.ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_LP)
        self.spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.STANDBY)
        self.spf_cm._update_component_state(operatingmode=SPFOperatingMode.STANDBY_LP)

    def teardown_method(self):
        """Tear down context"""
        self.tango_context.stop()

    def test_configure_band_cmd_succeeds_when_dish_mode_is_standbyfp(
        self, event_store_class, caplog
    ):
        """Test ConfigureBand"""
        caplog.set_level(logging.DEBUG)

        main_event_store = event_store_class()
        progress_event_store = event_store_class()

        for attr in [
            "dishMode",
            "longRunningCommandResult",
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

        assert main_event_store.wait_for_value(DishMode.STANDBY_LP, timeout=5)

        # Clear out the queue to make sure we don't catch old events
        main_event_store.clear_queue()

        [[_], [unique_id]] = self.device_proxy.SetStandbyFPMode()

        self.ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_FP)
        self.spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
        self.spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.DATA_CAPTURE)

        assert main_event_store.wait_for_command_id(unique_id, timeout=6)
        assert self.device_proxy.dishMode == DishMode.STANDBY_FP

        # Request ConfigureBand2 on Dish manager
        future_time = datetime.utcnow() + timedelta(days=1)
        [[_], [unique_id]] = self.device_proxy.ConfigureBand2(future_time.isoformat())

        self.spfrx_cm._update_component_state(configuredband=Band.B2)
        self.ds_cm._update_component_state(indexerposition=IndexerPosition.B2)
        self.spf_cm._update_component_state(bandinfocus=BandInFocus.B2)

        assert main_event_store.wait_for_command_id(unique_id, timeout=5)
        assert self.device_proxy.configuredBand == Band.B2

        expected_progress_updates = [
            "SetIndexPosition called on DS",
            "ConfigureBand2 called on SPFRx, ID",
            "Awaiting configuredband to transition to [B2]",
            "ConfigureBand2 completed",
        ]

        events = progress_event_store.wait_for_progress_update(
            expected_progress_updates[-1], timeout=6
        )

        events_string = "".join([str(event) for event in events])

        # Check that all the expected progress messages appeared
        # in the event store
        for message in expected_progress_updates:
            assert message in events_string
