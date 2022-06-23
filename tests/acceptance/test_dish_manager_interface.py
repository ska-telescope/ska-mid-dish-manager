"""Tests that check that the Dish Manager conforms to the ICD"""
import pytest
from tango import DeviceProxy
from tango_simlib.utilities.validate_device import validate_device_from_url

SPEC_URLS = {
    "dish_master": (
        "https://gitlab.com/ska-telescope/telescope-model/-/raw/"
        "master/spec/tango/dsh/DishMaster.yaml"
    ),
    "ska_tango_guide_ska_wide": (
        "https://gitlab.com/ska-telescope/telescope-model/-/raw/"
        "master/spec/tango/ska_wide/Guidelines.yaml"
    ),
}


@pytest.mark.acceptance
@pytest.mark.SKA_mid
def test_dish_manager_conforms_to_ska_wide_spec():
    """Test that the interface conforms to the base tango interface"""
    dish_manager_proxy = DeviceProxy("mid_d0001/elt/master")
    result = validate_device_from_url(
        dish_manager_proxy.name(),
        SPEC_URLS["ska_tango_guide_ska_wide"],
        False,
    )
    assert not result


@pytest.mark.acceptance
@pytest.mark.SKA_mid
def test_dish_manager_conforms_to_dish_master_spec():
    """Test that the device inteface conforms to the Dish Manager interface"""
    dish_manager_proxy = DeviceProxy("mid_d0001/elt/master"))
    result = validate_device_from_url(
        dish_manager_proxy.name(),
        SPEC_URLS["dish_master"],
        False,
    )
    assert not result
