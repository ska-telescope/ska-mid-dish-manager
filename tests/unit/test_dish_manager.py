import pytest
from tango.test_context import DeviceTestContext

from ska_mid_dish_manager.dish_manager import DishManager


@pytest.mark.unit
def test_dish_master():
    with DeviceTestContext(DishManager, process=True) as proxy:
        assert isinstance(proxy.ping(), int)
