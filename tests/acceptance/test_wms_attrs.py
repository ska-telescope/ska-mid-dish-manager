"""Tests to verify that dish manager monitors weather station device attributes."""

import pytest
from tango import AttrWriteType, DeviceProxy


@pytest.mark.acceptance
@pytest.mark.forked
def test_wms_read_attribute_type(dish_manager_proxy: DeviceProxy) -> None:
    """Test the wms attribute configurations are read only."""
    wind_gust_attribute_type = dish_manager_proxy.get_attribute_config("windGust").writable
    wind_speed_attribute_type = dish_manager_proxy.get_attribute_config("meanWindSpeed").writable
    assert wind_gust_attribute_type == AttrWriteType.READ
    assert wind_speed_attribute_type == AttrWriteType.READ
