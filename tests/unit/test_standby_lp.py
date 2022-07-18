import logging
from unittest.mock import MagicMock, patch

import pytest
from ska_tango_base.commands import ResultCode
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.dish_manager import DishManager
from ska_mid_dish_manager.models.dish_enums import DishMode


@pytest.mark.unit
@pytest.mark.forked
@patch("ska_mid_dish_manager.component_managers.tango_device_cm.tango")
def test_standby_in_lp(patched_tango, caplog):
    caplog.set_level(logging.DEBUG)

    # Set up mocks
    mocked_device_proxy = MagicMock()
    patched_tango.DeviceProxy = MagicMock(return_value=mocked_device_proxy)

    with DeviceTestContext(DishManager) as device_proxy:
        assert device_proxy.dishMode == DishMode.STANDBY_LP
        [[result_code], [_]] = device_proxy.SetStandbyLPMode()
        assert ResultCode(result_code) == ResultCode.QUEUED


@pytest.mark.unit
@pytest.mark.forked
@patch("ska_mid_dish_manager.component_managers.tango_device_cm.tango")
def test_standby_in_fp(patched_tango, caplog):
    caplog.set_level(logging.DEBUG)

    # Set up mocks
    patched_dp = MagicMock()
    patched_dp.command_inout = MagicMock()
    patched_tango.DeviceProxy = MagicMock(return_value=patched_dp)

    with DeviceTestContext(DishManager) as device_proxy:
        class_instance = DishManager.instances.get(device_proxy.name())
        class_instance.component_manager._update_component_state(
            dish_mode=DishMode.STANDBY_FP
        )
        assert device_proxy.dishMode == DishMode.STANDBY_FP
        [[result_code], [_]] = device_proxy.SetStandbyLPMode()
        assert ResultCode(result_code) == ResultCode.QUEUED
