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
        self, event_store, caplog
    ):
        """Test ConfigureBand"""
        caplog.set_level(logging.DEBUG)
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
        assert event_store.wait_for_value(DishMode.STANDBY_LP, timeout=5)

        # Clear out the queue to make sure we don't catch old events
        event_store.clear_queue()

        [[_], [unique_id]] = self.device_proxy.SetStandbyFPMode()

        self.ds_cm._update_component_state(
            operatingmode=DSOperatingMode.STANDBY_FP
        )
        self.spf_cm._update_component_state(
            operatingmode=SPFOperatingMode.OPERATE
        )
        self.spfrx_cm._update_component_state(
            operatingmode=SPFRxOperatingMode.DATA_CAPTURE
        )

        assert event_store.wait_for_command_id(unique_id, timeout=6)
        assert self.device_proxy.dishMode == DishMode.STANDBY_FP

        # Request ConfigureBand2 on Dish manager
        future_time = datetime.utcnow() + timedelta(days=1)
        [[_], [unique_id]] = self.device_proxy.ConfigureBand2(
            future_time.isoformat()
        )

        self.spfrx_cm._update_component_state(configuredband=Band.B2)
        self.ds_cm._update_component_state(indexerposition=IndexerPosition.B2)
        self.spf_cm._update_component_state(bandinfocus=BandInFocus.B2)

        assert event_store.wait_for_command_id(unique_id, timeout=5)
        assert self.device_proxy.configuredBand == Band.B2

    
    def test_configure_band_cmd_progress_updates(self, event_store):
        """Execute tests"""
        self.device_proxy.subscribe_event(
            "longRunningCommandProgress",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        # Subscribe to longRunningCommandResult so that we can see when the
        # function has completed with wait_for_command_id
        self.device_proxy.subscribe_event(
            "longRunningCommandResult",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        sub_id = self.device_proxy.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )
        assert event_store.wait_for_value(DishMode.STANDBY_LP, timeout=6)
        # unsubscribe to stop listening for dishMode events
        self.device_proxy.unsubscribe_event(sub_id)
        # Clear out the queue to make sure we dont keep previous events
        event_store.clear_queue()

        self.dish_manager_cm._update_component_state(configuredband=Band.B2)

        # Transition DishManager to STANDBY_FP mode
        [[_], [unique_id]] = self.device_proxy.SetStandbyFPMode()

        # transition subservient devices to FP mode and observe that
        # DishManager transitions dishMode to FP mode after all
        # subservient devices are in FP
        self.ds_cm._update_component_state(
            operatingmode=DSOperatingMode.STANDBY_FP
        )
        self.ds_cm._update_component_state(powerstate=DSPowerState.FULL_POWER)
        self.spf_cm._update_component_state(
            operatingmode=SPFOperatingMode.OPERATE
        )
        self.spf_cm._update_component_state(
            powerstate=SPFPowerState.FULL_POWER
        )
        self.spfrx_cm._update_component_state(
            operatingmode=SPFRxOperatingMode.DATA_CAPTURE
        )

        events = event_store.wait_for_command_id(unique_id, timeout=6)

        events_string = "".join([str(event) for event in events])

        expected_progress_updates = [
            "SetIndexPosition called on DS",
            (
                "Awaiting DS indexerposition to change to "
                "[<IndexerPosition.B2: 2>]"
            ),
            "ConfigureBand2 called on SPFRX",
            (
                "Awaiting SPFRX configuredband to change to "
                "[<Band.B2: 2>"
            ),
            "Awaiting dishmode change to 3",
            (
                "SPF operatingmode changed to, "
                "[<SPFOperatingMode.OPERATE: 3>]"
            ),
            (
                "SPFRX configuredband changed to, "
                "[<Band.B2: 2>]"
            ),
            "ConfigureBand2 completed",
        ]

        for message in expected_progress_updates:
            assert message in events_string