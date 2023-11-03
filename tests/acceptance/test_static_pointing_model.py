"""Test Static Pointing Model."""
from typing import Any

import pytest
import tango


@pytest.mark.acceptance
@pytest.mark.forked
def test_read_band2_static_pointing_model_parameters(
    dish_manager_proxy: tango.DeviceProxy,
) -> None:
    """Test Band2 Static Pointing Model Parameters."""
    band2_pointing_model_params = dish_manager_proxy.band2PointingModelParams

    assert len(band2_pointing_model_params) == 20
    assert band2_pointing_model_params.dtype.name == "float32"  # type: ignore


@pytest.mark.acceptance
@pytest.mark.forked
def test_write_band2_static_pointing_model_parameters(
    dish_manager_proxy: tango.DeviceProxy, event_store_class
) -> None:
    """Test Band2 Static Pointing Model Parameters."""
    write_values = [1.2, 3.4]

    dish_manager_proxy.band2PointingModelParams = write_values

    expected_values = [0.0] * 20
    expected_values[11] = write_values[0]  # CAobs
    expected_values[19] = write_values[1]  # Eobs

    model_event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        "band2PointingModelParams", tango.EventType.CHANGE_EVENT, model_event_store
    )
    model_event_store.wait_for_value(expected_values, timeout=7)


@pytest.mark.acceptance
@pytest.mark.forked
def test_track_load_static_off(
    dish_manager_proxy: tango.DeviceProxy, event_store_class: Any
) -> None:
    """Test Band2 Static Pointing Model Parameters."""
    write_values = [20.1, 0.5]
    ca_obs_index = 11
    e_obs_index = 19

    dish_manager_proxy.TrackLoadStaticOff(write_values)

    expected_values = [0.0] * 20
    expected_values[ca_obs_index] = write_values[0]
    expected_values[e_obs_index] = write_values[1]

    model_event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        "band2PointingModelParams", tango.EventType.CHANGE_EVENT, model_event_store
    )
    model_event_store.wait_for_value(expected_values, timeout=7)
