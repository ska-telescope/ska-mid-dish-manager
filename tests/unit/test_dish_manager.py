"""Unit tests checking DishManager behaviour."""
# pylint: disable=protected-access
# pylint: disable=attribute-defined-outside-init


import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import tango
from ska_control_model import CommunicationStatus, TaskStatus
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.DishManagerDS import DishManager
from ska_mid_dish_manager.models.dish_enums import (
    Band,
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
            "ska_mid_dish_manager.component_managers.device_monitor.tango"
        ) as patched_tango:
            patched_tango.DeviceProxy.return_value = MagicMock()
            patched_tango.DeviceProxy.command_inout = MagicMock()
            patched_tango.DeviceProxy.command_inout.return_value = (
                TaskStatus.COMPLETED,
                "Task Done",
            )

            self.tango_context = DeviceTestContext(DishManager)
            self.tango_context.start()

            self.device_proxy = self.tango_context.device
            class_instance = DishManager.instances.get(self.device_proxy.name())
            self.ds_cm = class_instance.component_manager.sub_component_managers["DS"]
            self.spf_cm = class_instance.component_manager.sub_component_managers["SPF"]
            self.spfrx_cm = class_instance.component_manager.sub_component_managers["SPFRX"]

            self.dish_manager_cm = class_instance.component_manager

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

        # band should be configured to call command on SPFRx device
        # and have it propagated to the long running command result
        self.dish_manager_cm._update_component_state(configuredband=Band.B2)
        self.dish_manager_cm._update_component_state(configuredband=Band.B3)

        self.device_proxy.subscribe_event(
            "longRunningCommandResult",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        self.device_proxy.SetStandbyFPMode()

        self.ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_FP)
        self.spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
        self.spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.DATA_CAPTURE)

        # Sample events:
        # ('longRunningCommandResult', ('', ''))

        # ('longrunningcommandresult',
        # ('1659015778.0797186_172264627776495_DS_SetStandbyFPMode',
        #  '"result"'))

        # ('longrunningcommandresult',
        # ('1659015778.0823436_222123736715640_SPF_SetOperateMode',
        # '"result"'))

        # ('longrunningcommandresult',
        # ('1659015778.0741146_217952885485963_SetStandbyFPMode',
        # '"{\\"DS\\": \\"16598.0786_1795_DS_SetStandbyFPMode\\",
        # \\"SPF\\": \\"1659778.0826_2215640_SPF_SetOperateMode\\",
        # \\"SPFRX\\": \\"16578.0925_1954609_SPFRX_CaptureData\\"}"'))

        # ('longrunningcommandresult',
        # ('16590178.0985_1954609_SPFRX_CaptureData', '"result"'))

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
        assert len(json.loads(self.tango_context.device.GetComponentStates())) == 3

    def test_desired_pointing_write(self):
        """Test that the write method of the desiredPointing attribute functions correctly"""
        mocked_write = MagicMock()
        self.ds_cm.write_attribute_value = mocked_write

        write_value = (0.0, 1.0, 2.0)

        self.device_proxy.desiredPointing = write_value

        mocked_write.assert_called()
        assert list(self.device_proxy.desiredPointing) == list(write_value)
