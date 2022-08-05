"""Test that the Dish Manager devices are available on startup"""
import pytest
import tango
from tango import DeviceProxy, DevState

from ska_mid_dish_manager.models.dish_enums import DishMode

@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.parametrize("dish_number", ["0001"])
def test_dishes_are_available(dish_number, event_store):
    """Test that the 4 dishes we expect are available"""
    dish_manager_proxy = DeviceProxy(f"mid_d{dish_number}/elt/master")
    assert isinstance(dish_manager_proxy.ping(), int)
    assert dish_manager_proxy.State() == DevState.STANDBY
    assert dish_manager_proxy.pointingState.name == "UNKNOWN"

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    event_store.wait_for_value(DishMode.STANDBY_LP, timeout=10)
    assert dish_manager_proxy.dishMode.name == "STANDBY_LP"
