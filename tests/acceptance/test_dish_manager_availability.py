import pytest

from tango import DeviceProxy, DevState


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.parametrize("dish_number", ["0001", "0002", "0003", "0004"])
def test_dishes_are_available(dish_number):
    """Test that the 4 dishes we expect are available"""
    dish_manager_proxy = DeviceProxy(f"mid_d{dish_number}/elt/master")
    assert isinstance(dish_manager_proxy.ping(), int)
    assert dish_manager_proxy.State() == DevState.STANDBY
    assert dish_manager_proxy.dishMode.name == "STANDBY_LP"
    assert dish_manager_proxy.pointingState.name == "NONE"
