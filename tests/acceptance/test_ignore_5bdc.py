"""Test setting ignoreB5dc attribute."""

import pytest
import tango


@pytest.mark.acceptance
@pytest.mark.forked
def test_set_ignore5bdc_attr(
    dish_manager_proxy: tango.DeviceProxy,
) -> None:
    """Test ignoreb5dc attribute."""
    assert not dish_manager_proxy.read_attribute("ignoreB5dc").value
    dish_manager_proxy.write_attribute("ignoreB5dc", True)
    assert dish_manager_proxy.read_attribute("ignoreB5dc").value
