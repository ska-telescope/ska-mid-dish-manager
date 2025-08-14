"""Test that DSC Control State can be read on Dish Manager's interface."""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import (
    DscCmdAuthType,
    DscCtrlState,
)


@pytest.mark.acceptance
@pytest.mark.forked
def test_dsccmdauth_attr(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
    ds_device_proxy,
):
    """Test DSC Control State can be read on Dish Manager."""
    dish_mode_event_store = event_store_class()

    sub_id = dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )
    # Check the DSC Control State on DSManager and Dish Manager
    # equate (DscCtrlState.REMOTE_CONTROL)This check also shows
    # dscCtrlState is not the default value (NO_AUTHORITY).
    assert (
        dish_manager_proxy.dscCtrlState
        == ds_device_proxy.dscCtrlState
        == DscCtrlState.REMOTE_CONTROL
    )

    # Check the DSC Command Authority on DSManager and Dish Manager equate.
    assert dish_manager_proxy.dscCmdAuth == ds_device_proxy.dscCmdAuth == DscCmdAuthType.LMC

    # Make DSManager release authority to test if the value is propagated.
    ds_device_proxy.ReleaseAuth()

    # Check that DSC Control State has been updated to NO_AUTHORITY.
    assert (
        ds_device_proxy.dscCtrlState
        == dish_manager_proxy.dscCtrlState
        == DscCtrlState.NO_AUTHORITY
    )

    dish_manager_proxy.unsubscribe_event(sub_id)
