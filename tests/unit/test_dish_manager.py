"""Unit tests checking DishManager behaviour."""
# pylint: disable=protected-access
# pylint: disable=attribute-defined-outside-init


import json
import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import tango
from ska_tango_base.executor import TaskStatus
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


# pylint: disable=missing-function-docstring
@pytest.mark.unit
@pytest.mark.forked
@patch("ska_mid_dish_manager.component_managers.tango_device_cm.tango")
def test_dish_manager_remains_in_startup_on_error(patched_tango, caplog):
    caplog.set_level(logging.DEBUG)

    # Set up mocks
    device_proxy = MagicMock()
    patched_tango.DeviceProxy = MagicMock(return_value=device_proxy)
    patched_tango.DevFailed = tango.DevFailed
    device_proxy.ping.side_effect = tango.DevFailed("FAIL")

    with DeviceTestContext(DishManager) as dish_manager:
        # check subservient devices are continously pinged whilst in error
        while device_proxy.ping.call_count < 5:
            continue
        assert device_proxy.ping.call_count >= 5
        # check that dishmanager remained in startup
        assert dish_manager.dishMode == DishMode.STARTUP
        dish_manager.AbortCommands()


class TestDishManagerBehaviour:
    """Tests DishManager"""

    def setup_method(self):
        """Set up context"""
        with patch(
            "ska_mid_dish_manager.component_managers." "tango_device_cm.tango.DeviceProxy"
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
        self.ds_cm = class_instance.component_manager.component_managers["DS"]
        self.spf_cm = class_instance.component_manager.component_managers["SPF"]
        self.spfrx_cm = class_instance.component_manager.component_managers["SPFRX"]
        self.dish_manager_cm = class_instance.component_manager
        # trigger transition to StandbyLP mode to
        # mimic automatic transition after startup
        self.ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_LP)
        self.spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.STANDBY)
        self.spf_cm._update_component_state(operatingmode=SPFOperatingMode.STANDBY_LP)

    def teardown_method(self):
        """Tear down context"""
        self.tango_context.stop()

    @pytest.mark.unit
    @pytest.mark.forked
    def test_device_reports_long_running_results(self, caplog, event_store):
        caplog.set_level(logging.DEBUG)
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

        dish_manager.subscribe_event(
            "longRunningCommandResult",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )
        # band should be configured to call command on SPFRx device
        # and have it propagated to the long running command result
        self.dish_manager_cm._update_component_state(configuredband=Band.B2)

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
        # ('1659015778.0823436_222123736715640_SPF_SetStandbyFPMode',
        # '"result"'))

        # ('longrunningcommandresult',
        # ('1659015778.0741146_217952885485963_SetStandbyFPMode',
        # '"{\\"DS\\": \\"16598.0786_1795_DS_SetStandbyFPMode\\",
        # \\"SPF\\": \\"1659778.0826_2215640_SPF_SetStandbyFPMode\\",
        # \\"SPFRX\\": \\"16578.0925_1954609_SPFRX_SetStandbyFPMode\\"}"'))

        # ('longrunningcommandresult',
        # ('16590178.0985_1954609_SPFRX_SetStandbyFPMode', '"result"'))

        events = event_store.wait_for_n_events(5, timeout=6)
        event_values = event_store.get_data_from_events(events)
        event_ids = [
            event_value[1][0]
            for event_value in event_values
            if event_value[1] and event_value[1][0]
        ]
        # Sort via command creation timestamp
        event_ids.sort(key=lambda x: datetime.fromtimestamp((float(x.split("_")[0]))))
        assert "_SetStandbyFPMode" in event_ids[0]
        assert "_DS_SetStandbyFPMode" in event_ids[1]
        assert "_SPF_SetStandbyFPMode" in event_ids[2]
        assert "_SPFRX_SetStandbyFPMode" in event_ids[3]

    @pytest.mark.unit
    @pytest.mark.forked
    def test_get_component_state(self):
        assert len(json.loads(self.device_proxy.GetComponentStates())) == 3
