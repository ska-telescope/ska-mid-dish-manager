"""Test Static Pointing Model."""

from typing import Any

import pytest
import tango

CA_OBS_INDEX = 11
E_OBS_INDEX = 19


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
    pointing_model_params = dish_manager_proxy.read_attribute(tango_attribute).value
    dish_manager_proxy.write_attribute(tango_attribute, write_values)

    pointing_model_params[CA_OBS_INDEX] = write_values[0]
    pointing_model_params[E_OBS_INDEX] = write_values[1]

    dm_event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        tango_attribute, tango.EventType.CHANGE_EVENT, dm_event_store
    )

    # FIXME this is a workaround to force updates to be bubbled up to DishManager
    # It's not clear why attribute writes to sub component managers do not get
    # events flowing all through until this intervention is actioned
    # and trigger the update to the dish manager component manager
    dish_manager_proxy.SyncComponentStates()
    dm_event_store.wait_for_value(pointing_model_params)


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
    expected_values[CA_OBS_INDEX] = write_values[0]
    expected_values[E_OBS_INDEX] = write_values[1]

    dm_event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        tango_attribute, tango.EventType.CHANGE_EVENT, dm_event_store
    )

    # FIXME this is a workaround to force updates to be bubbled up to DishManager
    # It's not clear why attribute writes to sub component managers do not get
    # events flowing all through until this intervention is actioned
    # and trigger the update to the dish manager component manager
    dish_manager_proxy.SyncComponentStates()
    dm_event_store.wait_for_value(expected_values)
