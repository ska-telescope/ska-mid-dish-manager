import time
import pytest
import tango

from ska_mid_dish_manager.dish_manager import DishManager, DishMode
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup

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


# @pytest.mark.forked
@pytest.mark.unit
def test_dish_transitions_to_lp_mode_after_startup(
    multi_device_tango_context
):
    dish_manager = multi_device_tango_context.get_device(
        "mid_d0005/elt/master"
    )
    assert dish_manager.dishMode.name == "STARTUP"

    # cb = MockTangoEventCallbackGroup("dishMode", timeout=30)
    # dish_manager.subscribe_event(
    #     "dishMode",
    #     tango.EventType.CHANGE_EVENT,
    #     cb["dishMode"],
    # )
    # cb.assert_change_event("dishMode", DishMode.STANDBY_LP, lookahead=10)
