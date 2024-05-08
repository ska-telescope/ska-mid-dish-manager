"""Test Static Pointing Model."""
from typing import Any

import pytest
import tango


@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.parametrize(
    "tango_attribute",
    [
        ("band1PointingModelParams"),
        ("band2PointingModelParams"),
        ("band3PointingModelParams"),
        ("band4PointingModelParams"),
    ],
)
def test_read_band_static_pointing_model_parameters(
    tango_attribute: str, dish_manager_proxy: tango.DeviceProxy
) -> None:
    """Test BandN Static Pointing Model Parameters."""
    band_pointing_model_params = dish_manager_proxy.read_attribute(tango_attribute).value

    assert len(band_pointing_model_params) == 20
    assert band_pointing_model_params.dtype.name == "float32"  # type: ignore


@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.parametrize(
    "tango_attribute,write_values",
    [
        ("band1PointingModelParams", [1.2, 3.4]),
        ("band2PointingModelParams", [5.6, 7.8]),
        ("band3PointingModelParams", [9.10, 10.11]),
        ("band4PointingModelParams", [11.12, 13.14]),
    ],
)
def test_write_bands_static_pointing_model_parameters(
    tango_attribute: str,
    write_values: list[float],
    dish_manager_proxy: tango.DeviceProxy,
    event_store_class: Any,
) -> None:
    """Test Band Static Pointing Model Parameters."""
    current_values = dish_manager_proxy.read_attribute(tango_attribute).value

    dish_manager_proxy.write_attribute(tango_attribute, write_values)

    expected_values = current_values
    expected_values[11] = write_values[0]  # CAobs
    expected_values[19] = write_values[1]  # Eobs

    model_event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        tango_attribute, tango.EventType.CHANGE_EVENT, model_event_store
    )
    model_event_store.wait_for_value(expected_values, timeout=7)


@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.parametrize(
    "tango_attribute",
    [
        ("band1PointingModelParams"),
        ("band2PointingModelParams"),
        ("band3PointingModelParams"),
        ("band4PointingModelParams"),
    ],
)
def test_track_load_static_off(
    tango_attribute: str, dish_manager_proxy: tango.DeviceProxy, event_store_class: Any
) -> None:
    """Test TrackLoadStaticOff command."""
    # This ensures that BandForCorr is bandX so that we receive an update on
    # bandXPointingModelParams when calling TrackLoadStaticOff
    dish_manager_proxy.write_attribute(tango_attribute, [0.0, 0.0])

    write_values = [20.1, 0.5]

    dish_manager_proxy.TrackLoadStaticOff(write_values)

    expected_values = [0.0] * 20
    expected_values[11] = write_values[0]  # CAobs
    expected_values[19] = write_values[1]  # Eobs

    model_event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        tango_attribute, tango.EventType.CHANGE_EVENT, model_event_store
    )
    model_event_store.wait_for_value(expected_values, timeout=7)
