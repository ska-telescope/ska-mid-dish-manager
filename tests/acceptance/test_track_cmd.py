"""Test that DS goes into STOW and dishManager reports it"""
import pytest
import tango

from ska_mid_dish_manager.devices.test_devices.utils import set_configuredBand_b1
from ska_mid_dish_manager.models.dish_enums import Band, DishMode, PointingState


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_track_cmd(event_store_class, ds_device_proxy, dish_manager_proxy):
    """Test transition to STOW"""

    main_event_store = event_store_class()
    band_event_store = event_store_class()
    progress_event_store = event_store_class()

    for attr in [
        "dishMode",
        "longRunningCommandResult",
    ]:
        dish_manager_proxy.subscribe_event(
            attr,
            tango.EventType.CHANGE_EVENT,
            main_event_store,
        )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    [[_], [unique_id]] = dish_manager_proxy.SetStandbyFPMode()
    main_event_store.wait_for_command_id(unique_id, timeout=8)

    assert dish_manager_proxy.dishMode == DishMode.STANDBY_FP

    set_configuredBand_b1()

    dish_manager_proxy.subscribe_event(
        "configuredBand",
        tango.EventType.CHANGE_EVENT,
        band_event_store,
    )
    assert band_event_store.wait_for_value(Band.B1, timeout=8)

    [[_], [unique_id]] = dish_manager_proxy.SetOperateMode()
    main_event_store.wait_for_command_id(unique_id, timeout=8)

    [[_], [unique_id]] = dish_manager_proxy.Track()

    # Force a pointingstate update
    ds_device_proxy.pointingState = PointingState.SCAN
    ds_device_proxy.pointingState = PointingState.TRACK

    main_event_store.wait_for_command_id(unique_id, timeout=8)

    expected_progress_updates = [
        "Track called on DS, ID",
        "Awaiting target lock change",
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

    assert dish_manager_proxy.achievedTargetLock
