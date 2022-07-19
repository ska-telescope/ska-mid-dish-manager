"""Unit tests for setstandbylp command."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import tango
from ska_tango_base.commands import ResultCode
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.dish_manager import DishManager
from ska_mid_dish_manager.models.dish_enums import DishMode, OperatingMode


# pylint: disable=missing-function-docstring
@pytest.mark.unit
@pytest.mark.forked
@patch("ska_mid_dish_manager.component_managers.tango_device_cm.tango")
def test_standbylp_cmd_fails_from_standbylp_dish_mode(patched_tango, caplog):
    caplog.set_level(logging.DEBUG)

    # Set up mocks
    mocked_device_proxy = MagicMock()
    patched_tango.DeviceProxy = MagicMock(return_value=mocked_device_proxy)

    with DeviceTestContext(DishManager) as device_proxy:
        assert device_proxy.dishMode == DishMode.STANDBY_LP

        with pytest.raises(tango.DevFailed):
            _, _ = device_proxy.SetStandbyLPMode()


# pylint: disable=missing-function-docstring, protected-access, invalid-name
@pytest.mark.unit
@pytest.mark.forked
@patch("ska_mid_dish_manager.component_managers.tango_device_cm.tango")
def test_standbylp_cmd_succeeds_from_standbyfp_dish_mode(
    patched_tango, caplog
):
    caplog.set_level(logging.DEBUG)

    # Set up mocks
    patched_dp = MagicMock()
    patched_dp.command_inout = MagicMock()
    patched_tango.DeviceProxy = MagicMock(return_value=patched_dp)

    with DeviceTestContext(DishManager) as device_proxy:
        # Force dishMode into STANDBY-FP
        class_instance = DishManager.instances.get(device_proxy.name())
        class_instance.component_manager._update_component_state(
            dish_mode=DishMode.STANDBY_FP
        )
        ds_cm = class_instance.component_manager.component_managers["DS"]
        spf_cm = class_instance.component_manager.component_managers["SPF"]
        spfrx_cm = class_instance.component_manager.component_managers["SPFRX"]

        for cm in [ds_cm, spf_cm, spfrx_cm]:
            cm._update_component_state(operating_mode=OperatingMode.STANDBY_FP)

        assert device_proxy.dishMode == DishMode.STANDBY_FP

        cb = MockTangoEventCallbackGroup("longRunningCommandResult", timeout=5)
        sub_id = device_proxy.subscribe_event(
            "longRunningCommandResult",
            tango.EventType.CHANGE_EVENT,
            cb["longRunningCommandResult"],
        )

        [[result_code], [unique_id]] = device_proxy.SetStandbyLPMode()
        assert ResultCode(result_code) == ResultCode.QUEUED

        cb.assert_change_event("longRunningCommandResult", ("", ""))
        cb.assert_change_event(
            "longRunningCommandResult",
            (unique_id, '"SetStandbyLPMode queued on ds, spf and spfrx"'),
        )
        device_proxy.unsubscribe_event(sub_id)

        ds_cm._update_component_state(operating_mode=OperatingMode.STANDBY_LP)
        assert device_proxy.dishMode == DishMode.STANDBY_FP

        spf_cm._update_component_state(operating_mode=OperatingMode.STANDBY_LP)
        assert device_proxy.dishMode == DishMode.STANDBY_FP

        spfrx_cm._update_component_state(
            operating_mode=OperatingMode.STANDBY_LP
        )
        assert device_proxy.dishMode == DishMode.STANDBY_LP
