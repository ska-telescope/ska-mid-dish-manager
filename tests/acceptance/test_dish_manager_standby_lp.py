"""Test StandbyLP"""
import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode, DSOperatingMode


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_standby_lp_transition(event_store_class):
    """Test transition to Standby_LP"""
    dish_manager = tango.DeviceProxy("mid_d0001/elt/master")
    ds_device = tango.DeviceProxy("mid_d0001/lmc/ds_simulator")
    # Get at least one device into a known state
    ds_device.operatingMode = DSOperatingMode.STANDBY_FP

    dish_mode_event_store = event_store_class()
    progress_event_store = event_store_class()

    dish_manager.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )
    dish_manager.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    dish_manager.SetStandbyLPMode()
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_LP, timeout=10)

    expected_progress_updates = [
        "SetStandbyLPMode called on DS",
        (
            "Awaiting DS operatingmode to change to "
            "[<DSOperatingMode.STANDBY_LP: 2>]"
        ),
        "SetStandbyLPMode called on SPF",
        (
            "Awaiting SPF operatingmode to change to "
            "[<SPFOperatingMode.STANDBY_LP: 2>]"
        ),
        "SetStandbyMode called on SPFRX",
        (
            "Awaiting SPFRX operatingmode to change to "
            "[<SPFRxOperatingMode.STANDBY: 2>]"
        ),
        "Awaiting dishmode change to 2",
        (
            "SPFRX operatingmode changed to, "
            "[<SPFRxOperatingMode.STANDBY: 2>]"
        ),
        ("DS operatingmode changed to, " "[<DSOperatingMode.STANDBY_LP: 2>]"),
        "SetStandbyLPMode completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string
