"""Test that the DishManager bandXPointingModelParams attributes
rejects invalid input."""

import pytest
import tango


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "tango_attribute,write_values",
    [
        ("band1PointingModelParams", [1.2]),
        ("band2PointingModelParams", [5.6, 7.8, 3.0]),
        (
            "band3PointingModelParams",
            [
                9.10,
            ],
        ),
        ("band4PointingModelParams", [11.12, 13.14, 19.0]),
    ],
)
def test_band_X_pointing_model_params_validation_checks(
    tango_attribute,
    write_values,
    dish_manager_resources,
):
    """Test bandxPointingModelParams rejects invalid input."""
    device_proxy, _ = dish_manager_resources
    try:
        device_proxy.write_attribute(tango_attribute, write_values)
    except tango.DevFailed as err:
        expected_desc = (
            "ValueError: Expected 2 arguments (off_xel, off_el) "
            f"but got {len(write_values)} arg(s)."
        )
        assert (err.args[0].desc).strip() == expected_desc
