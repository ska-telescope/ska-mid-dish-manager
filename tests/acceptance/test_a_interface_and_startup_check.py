"""Test that the Dish Manager devices conforms to the ICD and are available on startup."""

import pytest
from tango import DeviceProxy, DevState
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
@pytest.mark.parametrize("dish_number", ["001", "111"])
def test_dishes_are_available(monitor_tango_servers, dish_number):
    """Test that the 2 dishes we expect are available."""
    dish_manager_proxy = DeviceProxy(f"mid-dish/dish-manager/SKA{dish_number}")
    assert isinstance(dish_manager_proxy.ping(), int)
    assert dish_manager_proxy.State() == DevState.ON


@pytest.mark.acceptance
@pytest.mark.xfail
def test_dish_manager_conforms_to_ska_wide_spec(dish_manager_proxy):
    """Test that the interface conforms to the base tango interface."""
    result = validate_device_from_url(
        dish_manager_proxy.name(),
        SPEC_URLS["ska_tango_guide_ska_wide"],
        False,
    )
    assert not result


@pytest.mark.acceptance
@pytest.mark.xfail(reason="Pending changes on telescope model to dtype_out")
def test_dish_manager_conforms_to_dish_master_spec(dish_manager_proxy):
    """Test that the device interface conforms to the Dish Manager interface."""
    result = validate_device_from_url(
        dish_manager_proxy.name(),
        SPEC_URLS["dish_manager"],
        False,
    )
    assert not result


@pytest.mark.acceptance
@pytest.mark.xfail
def test_dish_manager_conforms_to_ska_controller_spec(dish_manager_proxy):
    """Test that the device interface conforms to the Dish Manager interface."""
    result = validate_device_from_url(
        dish_manager_proxy.name(),
        SPEC_URLS["ska_controller"],
        False,
    )
    assert not result


@pytest.mark.acceptance
@pytest.mark.xfail
def test_dish_manager_conforms_to_ska_tango_base_spec(dish_manager_proxy):
    """Test that the device interface conforms to the Dish Manager interface."""
    result = validate_device_from_url(
        dish_manager_proxy.name(),
        SPEC_URLS["ska_tango_base"],
        False,
    )
    assert not result
