"""Test that DS goes into STOW and dishManager reports it"""
import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode, DSOperatingMode


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_stow_transition(event_store_class):
    """Test transition to STOW"""
    dish_manager = tango.DeviceProxy("mid_d0001/elt/master")
    ds_device = tango.DeviceProxy("mid_d0001/lmc/ds_simulator")
    # Get at least one device into a known state
    ds_device.operatingMode = DSOperatingMode.STANDBY_FP

    main_event_store = event_store_class()
    progress_event_store = event_store_class()

    dish_manager.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )

    dish_manager.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    dish_manager.SetStowMode()

    assert main_event_store.wait_for_value(DishMode.STOW, timeout=6)

    expected_progress_updates = [
        "Stow called on DS",
        "Waiting for dishMode change to STOW",
        "Stow completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event) for event in events])
    for message in expected_progress_updates:
        assert message in events_string
