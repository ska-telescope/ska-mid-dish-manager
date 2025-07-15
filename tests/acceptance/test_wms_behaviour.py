"""Tests to verify that dish manager monitors weather station device attributes."""

import pytest
import tango
from tango import AttrWriteType, DeviceProxy


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
def test_change_events_configured_for_wind_gust(
    dish_manager_proxy: DeviceProxy, event_store_class
) -> None:
    """Test that the windGust attribute pushes change events."""
    main_event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        "windGust",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )

    windgust_event_value = main_event_store.get_queue_values()
    assert windgust_event_value


@pytest.mark.acceptance
@pytest.mark.forked
def test_change_events_configured_for_mean_wind_speed(
    dish_manager_proxy: DeviceProxy, event_store_class
) -> None:
    """Test that the meanWindSpeed attribute pushes change events."""
    main_event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        "meanWindSpeed",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )

    mean_windspeed_event_value = main_event_store.get_queue_values()
    assert mean_windspeed_event_value
