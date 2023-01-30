"""Test StandbyFP"""
import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_standby_fp_transition(event_store_class):
    """Test transition to Standby_FP"""
    dish_manager = tango.DeviceProxy("mid_d0001/elt/master")

    dish_mode_event_store = event_store_class()
    progress_event_store = event_store_class()

    dish_manager.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )
    # Make sure the intial dish mode is STANDBY LP
    dish_manager.SetStandbyLPMode()
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_LP, timeout=10)

    dish_manager.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    dish_manager.SetStandbyFPMode()
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=10)

    expected_progress_updates = [
        "SetStandbyFPMode called on DS",
        (
            "Awaiting DS operatingmode to change to "
            "[<DSOperatingMode.STANDBY_FP: 3>]"
        ),
        "SetOperateMode called on SPF",
        (
            "Awaiting SPF operatingmode to change to "
            "[<SPFOperatingMode.OPERATE: 3>]"
        ),
        "CaptureData called on SPFRX",
        (
            "Awaiting SPFRX operatingmode to change to "
            "[<SPFRxOperatingMode.STANDBY: 2>, "
            "<SPFRxOperatingMode.DATA_CAPTURE: 3>]"
        ),
        "Awaiting dishmode change to 3",
        ("SPF operatingmode changed to, [<SPFOperatingMode.OPERATE: 3>]"),
        (
            "SPFRX operatingmode changed to, "
            "[<SPFRxOperatingMode.STANDBY: 2>, "
            "<SPFRxOperatingMode.DATA_CAPTURE: 3>]"
        ),
        "SetStandbyFPMode completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string