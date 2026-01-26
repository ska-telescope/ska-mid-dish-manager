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
def test_ska001_is_available(monitor_tango_servers, reset_dish_to_standby, dish_manager_proxy):
    """Test that SKA001 is available."""
    assert isinstance(dish_manager_proxy.ping(), int)
    assert dish_manager_proxy.State() in [DevState.ON, DevState.ALARM]


@pytest.mark.acceptance
def test_other_dish_instance_is_available():
    """Test that a different, arbitrary dish is available."""
    dev_proxy = DeviceProxy("mid-dish/dish-manager/MKT111")
    assert isinstance(dev_proxy.ping(), int)
    assert dev_proxy.State() in [DevState.ON, DevState.ALARM]


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
