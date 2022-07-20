"""Unit tests checking DishManager behaviour."""

import logging
from unittest.mock import MagicMock, call, patch

import pytest
import tango
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.dish_manager import DishManager
from ska_mid_dish_manager.models.dish_enums import DishMode


# pylint: disable=invalid-name, missing-function-docstring
@pytest.fixture()
def devices_to_test(SimpleDevice):
    """Fixture for devices to test."""
    return [
        {
            "class": DishManager,
            "devices": [{"name": "mid_d0005/elt/master"}],
        },
        {
            "class": SimpleDevice,
            "devices": [
                {"name": "mid_d0001/lmc/ds_simulator"},
                {"name": "mid_d0001/spfrx/simulator"},
                {"name": "mid_d0001/spf/simulator"},
            ],
        },
    ]


# pylint: disable=invalid-name, missing-function-docstring
@pytest.mark.xfail(reason="Intermittent Segfaults")
@pytest.mark.forked
@pytest.mark.unit
def test_dish_manager_transitions_to_lp_mode_after_startup_no_mocks(
    multi_device_tango_context,
):
    dish_manager = multi_device_tango_context.get_device(
        "mid_d0005/elt/master"
    )
    assert dish_manager.dishMode.name == "STARTUP"

    cb = MockTangoEventCallbackGroup("dishMode", timeout=3)
    dish_manager.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        cb["dishMode"],
    )
    cb.assert_change_event("dishMode", DishMode.STANDBY_LP)


# pylint: disable=missing-function-docstring
@pytest.mark.unit
@pytest.mark.forked
@patch("ska_mid_dish_manager.component_managers.tango_device_cm.tango")
def test_dish_manager_transitions_to_lp_mode_after_startup_with_mocks(
    patched_tango,
):
    # Set up mocks
    device_proxy = MagicMock()
    patched_tango.DeviceProxy = MagicMock(return_value=device_proxy)

    with DeviceTestContext(DishManager) as dish_manager:
        assert dish_manager.dishMode == DishMode.STANDBY_LP

    # Check that we create the DeviceProxy
    assert patched_tango.DeviceProxy.call_count == 3
    for device_name in [
        "mid_d0001/lmc/ds_simulator",
        "mid_d0001/spfrx/simulator",
        "mid_d0001/spf/simulator",
    ]:
        assert call(device_name) in patched_tango.DeviceProxy.call_args_list

    # Check that we subscribe
    assert device_proxy.subscribe_event.call_count == 3


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
        assert dish_manager.dishMode == DishMode.STARTUP
        dish_manager.AbortCommands()
