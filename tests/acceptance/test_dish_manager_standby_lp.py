"""Test StandbyLP"""
import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode, DSOperatingMode


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_standby_lp_transition(event_store):
    """Test transisiotn to Standby_LP"""
    dish_manager = tango.DeviceProxy("mid_d0001/elt/master")
    ds_device = tango.DeviceProxy("mid_d0001/lmc/ds_simulator")
    # Get at least one device into a known state
    ds_device.SetOperatingMode(DSOperatingMode.STANDBY_FP)
    spf_device = tango.DeviceProxy("mid_d0001/spf/simulator")
    sfprx_device = tango.DeviceProxy("mid_d0001/spfrx/simulator")

    dish_manager.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    # DishManager will only go to STANDBY_LP after the updates below
    sfprx_device.SetStandbyMode()
    for device in [ds_device, spf_device]:
        device.SetStandbyLPMode()

    event_store.wait_for_value(DishMode.STANDBY_LP, timeout=10)
