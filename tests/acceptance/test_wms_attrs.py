"""Tests to verify that dish manager monitors weather station device attributes."""

import pytest
import tango


@pytest.mark.acceptance
def test_wms_read_attribute_type(dish_manager_proxy) -> None:
    """Test the wms attribute configurations are read only."""
    wind_gust_attribute_type = dish_manager_proxy.get_attribute_config("windGust").writable
    wind_speed_attribute_type = dish_manager_proxy.get_attribute_config("meanWindSpeed").writable
    assert wind_gust_attribute_type == tango.AttrWriteType.READ
    assert wind_speed_attribute_type == tango.AttrWriteType.READ


@pytest.mark.acceptance
@pytest.mark.parametrize(
    "attr_name",
    [
        "windGust",
        "meanWindSpeed",
    ],
)
def test_emits_change_event_for_wind_attrs(attr_name, dish_manager_proxy, event_store_class):
    """Test that dish manager gets wind gust updates."""
    event_store = event_store_class()
    event_id = dish_manager_proxy.subscribe_event(
        attr_name, tango.EventType.CHANGE_EVENT, event_store
    )
    assert event_store.wait_for_n_events(1, timeout=6)
    dish_manager_proxy.unsubscribe_event(event_id)
