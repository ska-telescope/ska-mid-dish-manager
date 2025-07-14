"""Tests to verify that dish manager monitors weather station device attributes."""

import pytest
import tango
from tango import AttrWriteType, DeviceProxy

DEFAULT_STARTING_VALUE = -1


@pytest.mark.acceptance
@pytest.mark.forked
def test_wms_read_attribute_type(dish_manager_proxy: DeviceProxy) -> None:
    """Test the wms attribute configurations are read only."""
    wind_gust_attribute_type = dish_manager_proxy.get_attribute_config("windGust").writable
    wind_speed_attribute_type = dish_manager_proxy.get_attribute_config("meanWindSpeed").writable
    assert wind_gust_attribute_type == AttrWriteType.READ
    assert wind_speed_attribute_type == AttrWriteType.READ


@pytest.mark.acceptance
@pytest.mark.forked
def test_wms_wind_gust_changes_over_time(
    dish_manager_proxy: DeviceProxy, event_store_class
) -> None:
    """Test that the windGust attribute changes over time."""
    main_event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        "windGust",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )
    main_event_store.clear_queue()

    windgust_event_value = main_event_store.get_queue_values()[-1]
    last_windgust_reading = windgust_event_value[1]

    assert last_windgust_reading != DEFAULT_STARTING_VALUE


@pytest.mark.acceptance
@pytest.mark.forked
def test_wms_mean_wind_speed_is_readable(
    dish_manager_proxy: DeviceProxy, event_store_class
) -> None:
    """Test that the meanWindSpeed attribute changes over time."""
    main_event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        "meanWindSpeed",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )
    main_event_store.clear_queue()

    mean_wind_speed_event_value = main_event_store.get_queue_values(timeout=10)[-1]
    last_mean_wind_speed_reading = mean_wind_speed_event_value[1]

    assert last_mean_wind_speed_reading != DEFAULT_STARTING_VALUE
