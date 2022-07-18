import logging
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
import tango
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.dish_manager import DishManager
from ska_mid_dish_manager.models.dish_enums import DishMode


@pytest.mark.unit
@pytest.mark.forked
@patch("ska_mid_dish_manager.component_managers.tango_device_cm.tango")
def test_standby_in_lp(patched_tango, caplog):
    caplog.set_level(logging.DEBUG)

    # Set up mocks
    device_proxy = MagicMock()
    patched_tango.DeviceProxy = MagicMock(return_value=device_proxy)

    with DeviceTestContext(DishManager) as dm:
        assert dm.dishMode == DishMode.STANDBY_LP
        result_code, message = dm.SetStandbyLPMode()
        assert result_code == "1"
        assert message == "Task queued"


@pytest.mark.unit
@pytest.mark.forked
@patch("ska_mid_dish_manager.component_managers.tango_device_cm.tango")
def test_standby_in_fp(patched_tango, caplog):
    caplog.set_level(logging.DEBUG)

    # Set up mocks
    device_proxy = MagicMock()
    patched_tango.DeviceProxy = MagicMock(return_value=device_proxy)

    with DeviceTestContext(DishManager) as dm:
        assert dm.name()
