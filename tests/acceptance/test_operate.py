"""Test that DS goes into STOW and dishManager reports it"""
import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
    DSOperatingMode,
)


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_stow_transition(event_store_class):
    """Test transition to OPERATE"""
    dish_manager = tango.DeviceProxy("mid_d0001/elt/master")
    ds_device = tango.DeviceProxy("mid_d0001/lmc/ds_simulator")
    # Get at least one device into a known state
    ds_device.operatingMode = DSOperatingMode.STANDBY_FP

    dish_manager.SetStandbyLPMode()
    main_event_store = event_store_class()
    progress_event_store = event_store_class()
    configuredband_event_store = event_store_class()

    dish_manager.subscribe_event(
        "configuredband",
        tango.EventType.CHANGE_EVENT,
        configuredband_event_store,
    )
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
    dish_manager.SetStandbyFPMode()
    main_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=6)

    dish_manager.ConfiguredBand2()
    assert dish_manager.configuredBand == Band.B2

    dish_manager.SetOperateMode()
    main_event_store.wait_for_value(DishMode.OPERATE, timeout=6)

    expected_progress_updates = [
        "SetPointMode called on DS",
        (
            "Awaiting DS operatingmode to change to "
            "[<DSOperatingMode.POINT: 7>]"
        ),
        "SetOperateMode called on SPF",
        (
            "Awaiting SPF operatingmode to change to "
            "[<SPFOperatingMode.OPERATE: 3>]"
        ),
        "CaptureData called on SPFRX",
        (
            "Awaiting SPFRX operatingmode to change to "
            "[<SPFRxOperatingMode.DATA_CAPTURE: 3>]"
        ),
        "Awaiting dishmode change to 7",
        ("DS operatingmode changed to, [<DSOperatingMode.POINT: 7>]"),
        ("SPF operatingmode changed to, " "[<SPFOperatingMode.OPERATE: 3>]"),
        (
            "SPFRX operatingmode changed to, "
            "[<SPFRxOperatingMode.DATA_CAPTURE: 3>]"
        ),
        "SetOperateMode completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event) for event in events])
    for message in expected_progress_updates:
        assert message in events_string
