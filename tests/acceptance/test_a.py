"""Test sleep"""
import time

import pytest


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_sleep(dish_manager_proxy):
    """Test sleep"""
    print("BBBefore")
    print(dish_manager_proxy.getComponentStates())

    time.sleep(60)

    print("AAAfter")
    print(dish_manager_proxy.getComponentStates())
