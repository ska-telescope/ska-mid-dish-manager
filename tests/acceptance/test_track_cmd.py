"""Test that DS goes into STOW and dishManager reports it"""
import pytest
import tango

from ska_mid_dish_manager.devices.test_devices.utils import (
    set_configuredBand_b1,
)
from ska_mid_dish_manager.models.dish_enums import Band, DishMode


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_track_cmd(event_store_class):
    """Test transition to STOW"""
    dish_manager = tango.DeviceProxy("mid_d0001/elt/master")
    # ds_device = tango.DeviceProxy("mid_d0001/lmc/ds_simulator")
    # # Get at least one device into a known state
    # ds_device.operatingMode = DSOperatingMode.STANDBY_FP

    main_event_store = event_store_class()
    progress_event_store = event_store_class()

    dish_manager.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )

    dish_manager.subscribe_event(
        "configuredBand",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )

    dish_manager.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    [[_], [unique_id]] = dish_manager.SetStandbyFPMode()
    main_event_store.wait_for_command_id(unique_id, timeout=8)

    assert dish_manager.dishMode == DishMode.STANDBY_FP

    set_configuredBand_b1()

    assert main_event_store.wait_for_value(Band.B1)

    dish_manager.SetOperateMode()

    # Wait for the operate command to complete
    assert main_event_store.wait_for_value(DishMode.OPERATE)

    progress_event_store.wait_for_progress_update(
        "SetOperateMode completed", timeout=6
    )

    dish_manager.Track()

    expected_progress_updates = [
        "Track called on DS",
        (
            "Awaiting DS operatingmode to change to "
            "[<DSOperatingMode.POINT: 7>]"
        ),
        "Awaiting achievedtargetlock change to True",
        ("DS operatingmode changed to, [<DSOperatingMode.POINT: 7>]"),
        "Track completed",
    ]

    # Wait for the track command to complete
    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    # Check that all the expected progress messages appeared
    # in the event store
    events_string = "".join([str(event) for event in events])
    for message in expected_progress_updates:
        assert message in events_string

    assert dish_manager.achievedTargetLock
