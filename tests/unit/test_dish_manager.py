"""Unit tests checking DishManager behaviour."""
# pylint: disable=protected-access
# pylint: disable=attribute-defined-outside-init


import json
import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import tango
from ska_control_model import TaskStatus
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.DishManagerDS import DishManager
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
    DSOperatingMode,
    SPFOperatingMode,
    SPFRxOperatingMode,
)

LOGGER = logging.getLogger(__name__)


class TestDishManagerBehaviour:
    """Tests DishManager"""

    def setup_method(self):
        """Set up context"""
        with patch(
            "ska_mid_dish_manager.component_managers.device_monitor.tango.DeviceProxy"
        ) as patched_dp:
            patched_dp.return_value = MagicMock()
            patched_dp.command_inout = MagicMock()
            patched_dp.command_inout.return_value = (
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
        self.tango_context.stop()

    # pylint: disable=missing-function-docstring,
    @pytest.mark.unit
    @pytest.mark.forked
    def test_device_reports_long_running_results(self, event_store):
        dish_manager = self.device_proxy
        sub_id = dish_manager.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )
        assert event_store.wait_for_value(DishMode.STANDBY_LP, timeout=6)
        # unsubscribe to stop listening for dishMode events
        dish_manager.unsubscribe_event(sub_id)
        # Clear out the queue to make sure we dont keep previous events
        event_store.clear_queue()

        # band should be configured to call command on SPFRx device
        # and have it propagated to the long running command result
        self.dish_manager_cm._update_component_state(configuredband=Band.B2)
        self.dish_manager_cm._update_component_state(configuredband=Band.B3)

        dish_manager.subscribe_event(
            "longRunningCommandResult",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        _, command_id = self.device_proxy.SetStandbyFPMode()

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

        events = event_store.wait_for_command_id(command_id[0], timeout=8)
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

    # pylint: disable=missing-function-docstring,
    @pytest.mark.unit
    @pytest.mark.forked
    def test_get_component_state(self):
        assert len(json.loads(self.device_proxy.GetComponentStates())) == 3
