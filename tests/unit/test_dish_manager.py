import pytest
import time
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.dish_manager import DishManager
from ska_tango_testing.mock.tango import MockTangoEventCallbackGroup
from tango.server import Device
from tango import DevState

@pytest.mark.unit
def test_dish_master():
    with DeviceTestContext(DishManager, process=True) as proxy:
        assert isinstance(proxy.ping(), int)


class TestDevice(Device):
    def init_device(self):
        super(Device, self).init_device()
        self.set_state(DevState.ON)
        self.set_change_event("State", True, True)


@pytest.fixture(scope="module")
def devices_to_test():
    """Fixture for devices to test."""
    return [
        {
            "class": DishManager,
            "devices": [
                {"name": "mid_d0005/elt/master"}
            ],
        },
        {
            "class": TestDevice,
            "devices": [
                {"name": "mid_d0001/lmc/ds_simulator"},
                {"name": "mid_d0001/spfrx/simulator"},
                {"name": "mid_d0001/spf/simulator"},
            ],
        },
    ]


@pytest.mark.forked
def test_something(multi_device_tango_context, callback_group):
    dish_manager = multi_device_tango_context.get_device("mid_d0005/elt/master")
    callback_group["dish_mode_callback"].assert_change_event("STANDBY_LP")
    assert dish_manager.dishMode.name == "STANDBY_LP"
