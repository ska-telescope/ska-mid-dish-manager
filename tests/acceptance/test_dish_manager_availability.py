"""Test that the Dish Manager devices are available on startup."""

import pytest
from tango import DeviceProxy, DevState


@pytest.mark.acceptance
@pytest.mark.parametrize("dish_number", ["001", "111"])
def test_dishes_are_available(monitor_tango_servers, dish_number):
    """Test that the 2 dishes we expect are available."""
    dish_manager_proxy = DeviceProxy(f"mid-dish/dish-manager/SKA{dish_number}")
    assert isinstance(dish_manager_proxy.ping(), int)
    assert dish_manager_proxy.State() == DevState.ON
