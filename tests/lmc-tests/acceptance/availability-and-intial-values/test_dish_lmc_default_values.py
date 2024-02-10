"""Verify that the startup values for dish and the subelements are accurate
(R.LMC.SM.10, R.LMC.SM.2)
"""
import pytest
import tango
from utils import retrieve_attr_value

from ska_mid_dish_manager.models.dish_enums import DishMode


@pytest.mark.lmc
def test_dish_manager_startups_with_expected_dish_mode(monitor_tango_servers, event_store):
    """Test that dish master starts up with the expected dishMode"""
    dish_manager = tango.DeviceProxy("ska001/elt/master")
    dish_manager.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    event_store.wait_for_value(DishMode.STANDBY_LP)
    dish_mode = retrieve_attr_value(dish_manager, "dishMode")
    assert dish_mode == DishMode.STANDBY_LP.name


@pytest.mark.lmc
@pytest.mark.parametrize("dish_number", ["001"])
@pytest.mark.parametrize("family", ["ds-manager", "simulator-spfc", "simulator-spfrx"])
def test_sub_elements_startup_with_expected_operating_mode(dish_number, family):
    """
    Test that dish structure, spf and spfrx
    devices report expected startup values
    """
    tango_device_proxy = tango.DeviceProxy(f"mid-dish/{family}/SKA{dish_number}")
    expected_operating_mode = "STANDBY" if "spfrx" in family else "STANDBY_LP"
    assert tango_device_proxy.operatingMode.name.replace("-", "_") == expected_operating_mode
