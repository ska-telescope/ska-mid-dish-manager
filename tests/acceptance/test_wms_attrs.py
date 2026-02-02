"""Tests to verify that dish manager monitors weather station device attributes."""

import pytest
from tango import AttrWriteType


@pytest.mark.WMS
@pytest.mark.acceptance
def test_wms_read_attribute_type(dish_manager_proxy) -> None:
    """Test the wms attribute configurations are read only."""
    wind_gust_attribute_type = dish_manager_proxy.get_attribute_config("windGust").writable
    wind_speed_attribute_type = dish_manager_proxy.get_attribute_config("meanWindSpeed").writable
    assert wind_gust_attribute_type == AttrWriteType.READ
    assert wind_speed_attribute_type == AttrWriteType.READ


@pytest.mark.WMS
@pytest.mark.acceptance
def test_wind_gust_updates(dish_manager_proxy, event_store_class):
    """Test that dish manager gets wind gust updates."""
    event_store = event_store_class()
    wind_gust_default_value = -1.0
    # The simulator publishes updates at 1Hz. Waiting 3s is
    # sufficient to get the default value changed from -1.0.
    event_store.get_queue_values()

    assert dish_manager_proxy.windGust != wind_gust_default_value
