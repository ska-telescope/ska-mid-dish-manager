"""Test that DS goes into STOW and dishManager reports it"""
import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DSOperatingMode


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_stow_transition(event_store):
    """Test transition to STOW"""
    dish_manager = tango.DeviceProxy("mid_d0001/elt/master")
    ds_device = tango.DeviceProxy("mid_d0001/lmc/ds_simulator")
    # Get at least one device into a known state
    ds_device.operatingMode = DSOperatingMode.STANDBY_FP

    for attr in [
        "dishMode",
        "longRunningCommandProgress",
        "longRunningCommandResult",
    ]:

        dish_manager.subscribe_event(
            attr,
            tango.EventType.CHANGE_EVENT,
            event_store,
        )
    [[_], [unique_id]] = dish_manager.SetStowMode()

    events = event_store.wait_for_command_id(unique_id, timeout=6)
    events_string = "".join([str(event) for event in events])
    for message in ["Awaiting dishmode change to 5", "SetStowMode completed"]:
        assert message in events_string
