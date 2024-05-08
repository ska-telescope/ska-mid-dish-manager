"""Tests that check that the Dish Manager conforms to the ICD"""
import pytest
from tango_simlib.utilities.validate_device import validate_device_from_url

SPEC_URLS = {
    "dish_manager": (
        "https://gitlab.com/ska-telescope/ska-telmodel/-/raw/"
        "master/tmdata/software/tango/dsh/DishManager.yaml"
    ),
    "ska_controller": (
        "https://gitlab.com/ska-telescope/ska-telmodel/-/raw/"
        "master/tmdata/software/tango/ska_wide/SKAMaster.yaml"
    ),
    "ska_tango_base": (
        "https://gitlab.com/ska-telescope/ska-telmodel/-/raw/"
        "master/tmdata/software/tango/ska_wide/SKABaseDevice.yaml"
    ),
    "ska_tango_guide_ska_wide": (
        "https://gitlab.com/ska-telescope/ska-telmodel/-/raw/"
        "master/tmdata/software/tango/ska_wide/Guidelines.yaml"
    ),
}


@pytest.mark.acceptance
@pytest.mark.xfail
def test_dish_manager_conforms_to_ska_wide_spec(dish_manager_proxy):
    """Test that the interface conforms to the base tango interface"""
    result = validate_device_from_url(
        dish_manager_proxy.name(),
        SPEC_URLS["ska_tango_guide_ska_wide"],
        False,
    )
    assert not result


@pytest.mark.acceptance
@pytest.mark.xfail(reason="Pending changes on telescope model to dtype_out")
def test_dish_manager_conforms_to_dish_master_spec(dish_manager_proxy):
    """Test that the device interface conforms to the Dish Manager interface"""
    result = validate_device_from_url(
        dish_manager_proxy.name(),
        SPEC_URLS["dish_manager"],
        False,
    )
    assert not result


@pytest.mark.acceptance
@pytest.mark.xfail
def test_dish_manager_conforms_to_ska_controller_spec(dish_manager_proxy):
    """Test that the device interface conforms to the Dish Manager interface"""
    result = validate_device_from_url(
        dish_manager_proxy.name(),
        SPEC_URLS["ska_controller"],
        False,
    )
    assert not result


@pytest.mark.acceptance
@pytest.mark.xfail
def test_dish_manager_conforms_to_ska_tango_base_spec(dish_manager_proxy):
    """Test that the device interface conforms to the Dish Manager interface"""
    result = validate_device_from_url(
        dish_manager_proxy.name(),
        SPEC_URLS["ska_tango_base"],
        False,
    )
    assert not result
