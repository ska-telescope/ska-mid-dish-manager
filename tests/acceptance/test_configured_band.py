"""Test StandbyLP"""
import pytest
import tango

from ska_mid_dish_manager.devices.test_devices.utils import (
    set_configuredBand_b1,
    set_configuredBand_b2,
)
from ska_mid_dish_manager.models.dish_enums import Band


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_configured_band(event_store):
    """Test transition to Standby_LP"""
    dish_manager = tango.DeviceProxy("mid_d0001/elt/master")

    dish_manager.subscribe_event(
        "configuredBand",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    if dish_manager.configuredBand == Band.B1:
        set_configuredBand_b2()
        event_store.wait_for_value(Band.B2, timeout=8)
    else:
        set_configuredBand_b1()
        event_store.wait_for_value(Band.B1, timeout=8)
