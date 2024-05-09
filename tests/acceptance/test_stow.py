"""Test that DS goes into STOW and dishManager reports it"""
import pytest
import tango
from ska_control_model import ResultCode

from ska_mid_dish_manager.models.dish_enums import DishMode


# pylint: disable=too-many-locals,unused-argument
@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_stow_transition(
    monitor_tango_servers, event_store_class, dish_manager_proxy, ds_device_proxy
):
    """Test transition to STOW"""  # Get at least one device into a known state
    ds_device_proxy.SetStandbyFPMode()

    main_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )

    dish_manager_proxy.SetStowMode()
    [[result_code], [_]] = dish_manager_proxy.SetStowMode()
    assert ResultCode(result_code) == ResultCode.OK

    assert main_event_store.wait_for_value(DishMode.STOW, timeout=6)
