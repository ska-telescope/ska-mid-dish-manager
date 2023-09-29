"""Test that the Dish Manager devices are available on startup"""
import pytest
from tango import DeviceProxy, DevState


# pylint:disable=unused-argument
@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.parametrize("dish_number", ["001"])
def test_dishes_are_available(monitor_tango_servers, dish_number):
    """Test that the 4 dishes we expect are available"""
    dish_manager_proxy = DeviceProxy(f"ska{dish_number}/elt/master")
    assert isinstance(dish_manager_proxy.ping(), int)
    assert dish_manager_proxy.State() == DevState.STANDBY
    assert dish_manager_proxy.pointingState.name == "UNKNOWN"
