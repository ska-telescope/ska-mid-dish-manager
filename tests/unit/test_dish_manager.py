"""Unit tests checking DishManager behaviour."""
# pylint: disable=protected-access
# pylint: disable=attribute-defined-outside-init


import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import tango
from ska_control_model import CommunicationStatus
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.DishManagerDS import DishManager
from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    SPFOperatingMode,
    SPFRxOperatingMode,
)
from tests.utils import EventStore


@pytest.mark.unit
@pytest.mark.forked
class TestDishManager:
    """Tests for dish manager"""

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

            self.dish_manager_cm = class_instance.component_manager

            class_instance = DishManager.instances.get(self.device_proxy.name())
            for com_man in class_instance.component_manager.sub_component_managers.values():
                com_man._update_communication_state(
                    communication_state=CommunicationStatus.ESTABLISHED
                )

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
        self.tango_context.stop()

    def test_dish_manager_behaviour(self, event_store):
        """Test that SetStandbyFPMode does 3 result updates. DishManager, DS, SPF"""

        # trigger transition to StandbyLP mode to
        # mimic automatic transition after startup
        self.ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_LP)
        self.spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.STANDBY)
        self.spf_cm._update_component_state(operatingmode=SPFOperatingMode.STANDBY_LP)

        self.ds_cm._update_communication_state(CommunicationStatus.ESTABLISHED)
        self.spf_cm._update_communication_state(CommunicationStatus.ESTABLISHED)
        self.spfrx_cm._update_communication_state(CommunicationStatus.ESTABLISHED)

        event_store.clear_queue()

        sub_id = self.device_proxy.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )
        assert event_store.wait_for_value(DishMode.STANDBY_LP, timeout=8)
        # unsubscribe to stop listening for dishMode events
        self.device_proxy.unsubscribe_event(sub_id)
        # Clear out the queue to make sure we dont keep previous events
        event_store.clear_queue()

        self.device_proxy.subscribe_event(
            "longRunningCommandResult",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        self.device_proxy.SetStandbyFPMode()

        self.ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_FP)
        self.spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)

        # Sample events:
        # ('longrunningcommandresult',
        # ('1659015778.0797186_172264627776495_DS_SetStandbyFPMode',
        #  '[0, "result"]'))

        # ('longrunningcommandresult',
        # ('1659015778.0823436_222123736715640_SPF_SetOperateMode',
        # '[0, "result"]'))

        # ('longrunningcommandresult',
        # ('1680213846.5427592_258218647656556_SetStandbyFPMode',
        # '[0, "SetStandbyFPMode completed"]'))

        events = event_store.wait_for_n_events(4)
        event_values = event_store.get_data_from_events(events)
        event_ids = [
            event_value[1][0]
            for event_value in event_values
            if event_value[1] and event_value[1][0]
        ]
        # Sort via command creation timestamp
        event_ids.sort(key=lambda x: datetime.fromtimestamp((float(x.split("_")[0]))))
        assert sorted([event_id.split("_")[-1] for event_id in event_ids]) == [
            "SetOperateMode",
            "SetStandbyFPMode",
            "SetStandbyFPMode",
        ]

    def test_component_states(self):
        """Test that GetComponentStates for 3 devices are returned"""
        json_string = json.loads(self.tango_context.device.GetComponentStates())
        assert "DS" in json_string
        assert "SPFRx" in json_string
        assert "SPF" in json_string
