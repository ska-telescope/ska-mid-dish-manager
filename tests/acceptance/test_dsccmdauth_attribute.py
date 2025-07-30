"""Test that DSC Command Authority can be read on Dish Manager's interface."""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DscCmdAuthType,
)


@pytest.mark.acceptance
@pytest.mark.forked
def test_dsccmdauth_attr(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
    ds_device_proxy,
):
    """Test DSC Command Authority can be read on Dish Manager."""
    dish_mode_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )

    # Assumes that the initial state is FP -> Transition the dish to LP through Dish Manager
    dish_manager_proxy.SetStandbyLPMode()

    # Check that the command was successful
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_LP, timeout=8)

    # Check that DSC Command Authority has updated to LMC
    assert ds_device_proxy.dscCmdAuth == dish_manager_proxy.dscCmdAuth == DscCmdAuthType.LMC
