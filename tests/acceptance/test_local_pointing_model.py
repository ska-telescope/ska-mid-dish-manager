"""Test Static Pointing Model."""

import random
from typing import Any

import pytest
import tango

from ska_mid_dish_manager.models.constants import BAND_POINTING_MODEL_PARAMS_LENGTH


@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.parametrize(
    "tango_attribute",
    [
        ("band0PointingModelParams"),
        ("band1PointingModelParams"),
        ("band2PointingModelParams"),
        ("band3PointingModelParams"),
        ("band4PointingModelParams"),
        ("band5aPointingModelParams"),
        ("band5bPointingModelParams"),
    ],
)
def test_read_band_static_pointing_model_parameters(
    tango_attribute: str, dish_manager_proxy: tango.DeviceProxy
) -> None:
    """Test BandN Static Pointing Model Parameters."""
    band_pointing_model_params = dish_manager_proxy.read_attribute(tango_attribute).value

    assert len(band_pointing_model_params) == BAND_POINTING_MODEL_PARAMS_LENGTH
    assert band_pointing_model_params.dtype.name == "float64"  # type: ignore


@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.parametrize(
    "tango_attribute",
    [
        ("band0PointingModelParams"),
        ("band1PointingModelParams"),
        ("band2PointingModelParams"),
        ("band3PointingModelParams"),
        ("band4PointingModelParams"),
        ("band5aPointingModelParams"),
        ("band5bPointingModelParams"),
    ],
)
def test_write_bands_static_pointing_model_parameters(
    tango_attribute: str,
    dish_manager_proxy: tango.DeviceProxy,
    event_store_class: Any,
) -> None:
    """Test Band Static Pointing Model Parameters."""
    write_values = []
    abphi_index = 10

    for i in range(BAND_POINTING_MODEL_PARAMS_LENGTH):
        if i == abphi_index:  # abphi is the only one with unique range
            write_values.append(random.uniform(0, 360))
        else:
            write_values.append(random.uniform(-2000, 2000))

    invalid_write_values = write_values.copy()
    invalid_write_values[0] = 2001

    with pytest.raises(tango.DevFailed):
        dish_manager_proxy.write_attribute(tango_attribute, invalid_write_values)
    dish_manager_proxy.write_attribute(tango_attribute, write_values)

    model_event_store = event_store_class()
    sub_id = dish_manager_proxy.subscribe_event(
        tango_attribute, tango.EventType.CHANGE_EVENT, model_event_store
    )
    model_event_store.wait_for_value(write_values, timeout=7)
    dish_manager_proxy.unsubscribe_event(sub_id)
