"""Tests to verify weather station device attributes are readable and are configured as read types."""

from time import time
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
def test_wms_attributes_are_readable(dish_manager_proxy: DeviceProxy, event_store_class) -> None:
    """Test the wms attribute configurations are readable."""
    main_event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        "windGust",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )

    # wind_speed_default_val = -1
    wind_gust_default_val = -1.0
    time.sleep(10)
    # main_event_store.wait_for_n_events(1, timeout=6)
    mean_wg = dish_manager_proxy.read_attribute("windGust").value
    print(f"meanWG: {mean_wg}")

    # assert dish_manager_proxy.read_attribute("meanWindSpeed").value != wind_speed_default_val
    assert dish_manager_proxy.read_attribute("windGust").value != wind_gust_default_val
    main_event_store.clear_queue()
