"""Unit tests for the ConfigureBand2 command on dish manager."""

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
    SPFOperatingMode,
    SPFRxOperatingMode,
)
from tests.utils import EventStore

LOGGER = logging.getLogger(__name__)


# pylint:disable=attribute-defined-outside-init
# pylint:disable=protected-access
@pytest.mark.unit
@pytest.mark.forked
class TestConfigureBand:
    """Tests for ConfigureBand"""

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

            event_store = EventStore()
            self.device_proxy = self.tango_context.device

            class_instance = DishManager.instances.get(self.device_proxy.name())
            for com_man in class_instance.component_manager.sub_component_managers.values():
                com_man._update_communication_state(
                    communication_state=CommunicationStatus.ESTABLISHED
                )

            for conn_attr in ["spfConnectionState", "spfrxConnectionState", "dsConnectionState"]:
                self.device_proxy.subscribe_event(
                    conn_attr,
                    tango.EventType.CHANGE_EVENT,
                    event_store,
                )
                event_store.wait_for_value(CommunicationStatus.ESTABLISHED)

        self.device_proxy = self.tango_context.device
        class_instance = DishManager.instances.get(self.device_proxy.name())
        self.ds_cm = class_instance.component_manager.sub_component_managers["DS"]
        self.spf_cm = class_instance.component_manager.sub_component_managers["SPF"]
        self.spfrx_cm = class_instance.component_manager.sub_component_managers["SPFRX"]
        self.dish_manager_cm = class_instance.component_manager

        self.spf_cm.write_attribute_value = MagicMock()

        self.ds_cm.update_state_from_monitored_attributes = MagicMock()
        self.spf_cm.update_state_from_monitored_attributes = MagicMock()
        self.spfrx_cm.update_state_from_monitored_attributes = MagicMock()

        # trigger transition to StandbyLP mode to
        # mimic automatic transition after startup
        self.ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_LP)
        self.spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.STANDBY)
        self.spf_cm._update_component_state(operatingmode=SPFOperatingMode.STANDBY_LP)

    def teardown_method(self):
        """Tear down context"""
        return

    @pytest.mark.parametrize(
        "command,band_number",
        [
            ("ConfigureBand1", "B1"),
            ("ConfigureBand2", "B2"),
        ],
    )
    def test_configure_band_cmd_succeeds_when_dish_mode_is_standbyfp(
        self, command, band_number, event_store_class, caplog
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

        [[_], [unique_id]] = self.device_proxy.command_inout(command, False)

        self.spfrx_cm._update_component_state(configuredband=Band[band_number])
        self.ds_cm._update_component_state(indexerposition=IndexerPosition[band_number])
        self.spf_cm._update_component_state(bandinfocus=BandInFocus[band_number])

        assert main_event_store.wait_for_command_id(unique_id, timeout=5)
        assert self.device_proxy.configuredBand == Band[band_number]

        expected_progress_updates = [
            "SetIndexPosition called on DS",
            f"{command} called on SPFRx, ID",
            f"Awaiting configuredband change to {band_number}",
            f"{command} completed",
        ]

        events = progress_event_store.wait_for_progress_update(
            expected_progress_updates[-1], timeout=6
        )

        events_string = "".join([str(event) for event in events])

        # Check that all the expected progress messages appeared
        # in the event store
        for message in expected_progress_updates:
            assert message in events_string
