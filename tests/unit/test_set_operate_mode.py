"""Unit tests for setstandbylp command."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import tango
from ska_tango_base.commands import ResultCode
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.dish_manager import DishManager
from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    SPFOperatingMode,
    SPFRxOperatingMode,
)

LOGGER = logging.getLogger(__name__)


@pytest.mark.unit
@pytest.mark.forked
class TestSetOperateMode:
    """Tests for SetOperateMode"""

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

    def teardown_method(self):
        """Tear down context"""
        self.tango_context.stop()

    # pylint: disable=missing-function-docstring, protected-access
    def test_set_operate_mode_fails_when_already_in_operate_dish_mode(
        self,
        event_store,
    ):
        device_proxy = self.tango_context.device
        device_proxy.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        class_instance = DishManager.instances.get(device_proxy.name())
        ds_cm = class_instance.component_manager.component_managers["DS"]
        spf_cm = class_instance.component_manager.component_managers["SPF"]
        spfrx_cm = class_instance.component_manager.component_managers["SPFRX"]
        # Force dishManager dishMode to go to OPERATE
        ds_cm._update_component_state(operating_mode=DSOperatingMode.POINT)
        spf_cm._update_component_state(operating_mode=SPFOperatingMode.OPERATE)
        spfrx_cm._update_component_state(
            operating_mode=SPFRxOperatingMode.DATA_CAPTURE
        )
        event_store.wait_for_value(DishMode.OPERATE)

        with pytest.raises(tango.DevFailed):
            # Transition DishManager to OPERATE issuing a command
            _, _ = device_proxy.SetOperateMode()

    def test_set_operate_mode_succeeds_from_standbyfp_dish_mode(
        self,
        event_store,
    ):
        device_proxy = self.tango_context.device
        device_proxy.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )
        device_proxy.subscribe_event(
            "longRunningCommandResult",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        class_instance = DishManager.instances.get(device_proxy.name())
        ds_cm = class_instance.component_manager.component_managers["DS"]
        spf_cm = class_instance.component_manager.component_managers["SPF"]
        spfrx_cm = class_instance.component_manager.component_managers[
            "SPFRX"
        ]
        # Force dishManager dishMode to go to STANDBY_FP
        ds_cm._update_component_state(
            operating_mode=DSOperatingMode.STANDBY_FP
        )
        spf_cm._update_component_state(
            operating_mode=SPFOperatingMode.OPERATE
        )
        spfrx_cm._update_component_state(
            operating_mode=SPFRxOperatingMode.STANDBY
        )
        event_store.wait_for_value(DishMode.STANDBY_FP)

        # Transition DishManager to OPERATE issuing a command
        [[result_code], [unique_id]] = device_proxy.SetOperateMode()
        assert ResultCode(result_code) == ResultCode.QUEUED

        # wait for the SetOperateMode to be queued, i.e. the cmd
        # has been submitted to the subservient devices
        assert event_store.wait_for_command_result(
            unique_id, '"SetOperateMode queued on ds, spf and spfrx"'
        )

        # transition subservient devices to their respective operatingMode
        # and observe that DishManager transitions dishMode to OPERATE mode
        # SPF are already in the expected operatingMode
        ds_cm._update_component_state(
            operating_mode=DSOperatingMode.POINT
        )
        assert device_proxy.dishMode == DishMode.STANDBY_FP

        spfrx_cm._update_component_state(
            operating_mode=SPFRxOperatingMode.DATA_CAPTURE
        )
        # we can now expect dishMode to transition to OPERATE
        event_store.wait_for_value(DishMode.OPERATE)
