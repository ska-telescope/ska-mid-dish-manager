"""Test that DS goes into STOW and dishManager reports it"""
import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_stow_transition(event_store):
    """Test transition to STOW"""
    dish_manager = tango.DeviceProxy("mid_d0001/elt/master")
    ds_device = tango.DeviceProxy("mid_d0001/lmc/ds_simulator")
    # Get at least one device into a known state
    ds_device.SetStandbyFPMode()

    dish_manager.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    dish_manager.SetStowMode()
    event_store.wait_for_value(DishMode.STOW, timeout=8)
