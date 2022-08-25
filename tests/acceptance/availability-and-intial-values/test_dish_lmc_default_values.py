"""Verify that the startup values for dish and the subelements are accurate
(R.LMC.SM.10, R.LMC.SM.2)
"""
import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode
from tests.utils_testing import retrieve_attr_value


@pytest.mark.acceptance
@pytest.mark.SKA_mid
def test_dish_manager_startups_with_expected_dish_mode(event_store):
    """Test that dish master starts up with the expected dishMode"""
    dish_manager = tango.DeviceProxy("mid_d0001/elt/master")
    dish_manager.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    event_store.wait_for_value(DishMode.STANDBY_LP, timeout=60)
    dish_mode = retrieve_attr_value(dish_manager, "dishMode")
    assert dish_mode == DishMode.STANDBY_LP.name


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.parametrize("domain", ["0001"])
@pytest.mark.parametrize(
    "family_member", ["lmc/ds_simulator", "spf/simulator", "spfrx/simulator"]
)
def test_sub_elements_startup_with_expected_operating_mode(
    domain, family_member
):
    """Test that dish structure, spf and spfrx devices
    report expected startup values"""
    tango_device_proxy = tango.DeviceProxy(f"mid_d{domain}/{family_member}")
    expected_operating_mode = (
        "STANDBY" if "spfrx" in family_member else "STANDBY_LP"
    )
    assert tango_device_proxy.operatingMode.name == expected_operating_mode
