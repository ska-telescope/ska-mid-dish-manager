"""Test that DS goes into STOW and dishManager reports it"""
import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode, DSOperatingMode


# pylint: disable=too-many-locals,unused-argument
@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_stow_transition(
    monitor_tango_servers, event_store_class, dish_manager_proxy, ds_device_proxy
):
    """Test transition to STOW"""  # Get at least one device into a known state
    ds_device_proxy.operatingMode = DSOperatingMode.STANDBY_FP

    main_event_store = event_store_class()
    progress_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    dish_manager_proxy.SetStowMode()

    assert main_event_store.wait_for_value(DishMode.STOW, timeout=6)

    expected_progress_updates = [
        "Stow called on DS",
        "Awaiting dishMode change to STOW",
        "Stow completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event) for event in events])
    for message in expected_progress_updates:
        assert message in events_string
