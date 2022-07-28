"""Unit tests checking DishManager behaviour."""

import logging
from unittest.mock import MagicMock, call, patch

import pytest
import tango
from ska_tango_base.executor import TaskStatus
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.devices.dish_manager import DishManager
from ska_mid_dish_manager.devices.test_devices.DSDevice import DSDevice
from ska_mid_dish_manager.models.dish_enums import DishMode

LOGGER = logging.getLogger(__name__)


# pylint: disable=invalid-name, missing-function-docstring
@pytest.fixture()
def devices_to_test():
    """Fixture for devices to test."""
    return [
        {
            "class": DishManager,
            "devices": [{"name": "mid_d0005/elt/master"}],
        },
        {
            "class": DSDevice,
            "devices": [
                {"name": "mid_d0001/lmc/ds_simulator"},
                {"name": "mid_d0001/spfrx/simulator"},
                {"name": "mid_d0001/spf/simulator"},
            ],
        },
    ]


# pylint: disable=invalid-name, missing-function-docstring
@pytest.mark.forked
@pytest.mark.unit
def test_dish_manager_transitions_to_lp_mode_after_startup_no_mocks(
    multi_device_tango_context, event_store
):
    dish_manager = multi_device_tango_context.get_device(
        "mid_d0005/elt/master"
    )

    assert dish_manager.dishMode.name == "STARTUP"

    dish_manager.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    event_store.wait_for_value(DishMode.STARTUP)


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
        # Transition happens almost instantly on a fast machine,
        # even before we can complete event subscription or a MockCallable.
        # Give it a few tries for a slower machine
        for i in range(20):
            LOGGER.info("waiting for STANDBY_LP [%s]", i)
            if dish_manager.dishMode == DishMode.STANDBY_LP:
                break
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
    assert device_proxy.subscribe_event.call_count == 6


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


@pytest.mark.unit
@pytest.mark.forked
@patch(
    "ska_mid_dish_manager.component_managers.tango_device_cm.tango.DeviceProxy"
)
def test_device(patched_dp, event_store):
    patched_device_proxy = MagicMock()
    patched_dp.return_value = patched_device_proxy
    patched_dp.command_inout = MagicMock()
    patched_dp.command_inout.return_value = (TaskStatus.COMPLETED, "Task Done")

    with DeviceTestContext(DishManager, process=True) as dish_manager:

        dish_manager.subscribe_event(
            "longRunningCommandResult",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )
        dish_manager.SetStandbyFPMode()
        events = event_store.get_queue_values(timeout=3)
        assert len(events) == 5
