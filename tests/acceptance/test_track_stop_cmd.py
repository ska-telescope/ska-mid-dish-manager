"""Test that DS stops tracking and dishManager reports it"""
import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import Band, DishMode
from tests.utils import set_configuredBand_b1


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_track_stop_cmd(
    event_store_class, dish_manager_proxy, ds_device_proxy, spf_device_proxy, spfrx_device_proxy
):
    """Test TrackStop command"""

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

    set_configuredBand_b1(
        dish_manager_proxy, ds_device_proxy, spf_device_proxy, spfrx_device_proxy
    )

    dish_manager_proxy.subscribe_event(
        "configuredBand",
        tango.EventType.CHANGE_EVENT,
        band_event_store,
    )
    assert band_event_store.wait_for_value(Band.B1, timeout=8)

    [[_], [unique_id]] = dish_manager_proxy.SetOperateMode()
    main_event_store.wait_for_command_id(unique_id, timeout=8)

    [[_], [unique_id]] = dish_manager_proxy.Track()

    main_event_store.wait_for_command_id(unique_id, timeout=8)

    main_event_store.clear_queue()
    progress_event_store.clear_queue()

    # Call TrackStop on DishManager
    [[_], [unique_id]] = dish_manager_proxy.TrackStop()

    main_event_store.wait_for_command_id(unique_id, timeout=8)

    expected_progress_updates = [
        "TrackStop called on DS, ID",
        "Awaiting pointingstate change to READY",
        "TrackStop completed",
    ]

    # Wait for the track command to complete
    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=8
    )

    # Check that all the expected progress messages appeared
    # in the event store
    events_string = "".join([str(event) for event in events])

    for message in expected_progress_updates:
        assert message in events_string

    assert not dish_manager_proxy.achievedTargetLock
