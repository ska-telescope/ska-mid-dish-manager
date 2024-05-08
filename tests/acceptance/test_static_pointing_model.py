"""Test Static Pointing Model."""
from typing import Any

import pytest
import tango

CA_OBS_INDEX = 11
E_OBS_INDEX = 19


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
    dish_manager_proxy: tango.DeviceProxy,
    ds_device_proxy: tango.DeviceProxy,
    event_store_class: Any,
) -> None:
    """Test Band2 Static Pointing Model Parameters."""
    dm_event_store = event_store_class()
    ds_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "band2PointingModelParams", tango.EventType.CHANGE_EVENT, dm_event_store
    )

    ds_device_proxy.subscribe_event(
        "band2PointingModelParams", tango.EventType.CHANGE_EVENT, ds_event_store
    )

    write_values = [1.2, 3.4]
    expected_values = [0.0] * 20
    expected_values[CA_OBS_INDEX] = write_values[0]
    expected_values[E_OBS_INDEX] = write_values[1]

    dish_manager_proxy.band2PointingModelParams = write_values
    # verify that DS Manager received the update
    ds_event_store.wait_for_value(expected_values)

    # FIXME this is a workaround to force updates to be bubbled up to DishManager
    # It's not clear why attribute writes to sub component managers do not get
    # events flowing all through until this intervention is actioned
    # and trigger the update to the dish manager component manager
    dish_manager_proxy.SyncComponentStates()
    dm_event_store.wait_for_value(expected_values)


@pytest.mark.acceptance
@pytest.mark.forked
def test_track_load_static_off(
    dish_manager_proxy: tango.DeviceProxy,
    ds_device_proxy: tango.DeviceProxy,
    event_store_class: Any,
) -> None:
    """Test Band2 Static Pointing Model Parameters."""
    dm_event_store = event_store_class()
    ds_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "band2PointingModelParams", tango.EventType.CHANGE_EVENT, dm_event_store
    )

    ds_device_proxy.subscribe_event(
        "band2PointingModelParams", tango.EventType.CHANGE_EVENT, ds_event_store
    )

    write_values = [20.1, 0.5]
    expected_values = [0.0] * 20
    expected_values[CA_OBS_INDEX] = write_values[0]
    expected_values[E_OBS_INDEX] = write_values[1]

    dish_manager_proxy.TrackLoadStaticOff(write_values)
    # verify that DS Manager received the update
    ds_event_store.wait_for_value(expected_values)

    # FIXME this is a workaround to force updates to be bubbled up to DishManager
    # It's not clear why attribute writes to sub component managers do not get
    # events flowing all through until this intervention is actioned
    # and trigger the update to the dish manager component manager
    dish_manager_proxy.SyncComponentStates()
    dm_event_store.wait_for_value(expected_values)
