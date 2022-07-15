from unittest.mock import MagicMock, call, patch

import pytest
import tango
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.dish_manager import DishManager, DishMode


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


@pytest.mark.xfail(reason="Event system making test fail intermittently")
@pytest.mark.forked
@pytest.mark.unit
def test_dish_transitions_to_lp_mode_after_startup(multi_device_tango_context):
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
    cb.assert_change_event("dishMode", DishMode.STANDBY_LP, lookahead=10)


def test_dm_start_up_ok():
    with patch(
        "ska_mid_dish_manager.component_managers.tango_device_cm.tango"
    ) as patched_tango:
        # Set up mocks
        device_proxy = MagicMock()
        patched_tango.DeviceProxy = MagicMock(return_value=device_proxy)

        with DeviceTestContext(DishManager) as dm:
            # Check that we create the DeviceProxy
            assert patched_tango.DeviceProxy.call_count == 3
            for device_name in [
                "mid_d0001/lmc/ds_simulator",
                "mid_d0001/spfrx/simulator",
                "mid_d0001/spf/simulator",
            ]:
                assert (
                    call(device_name)
                    in patched_tango.DeviceProxy.call_args_list
                )

            # Check that we subscribe
            assert device_proxy.subscribe_event.call_count == 3

            # Check that we end up in the right state
            assert dm.dishMode == DishMode.STANDBY_LP
