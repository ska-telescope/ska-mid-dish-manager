"""Test ResetTrackTable on dish manager."""

import pytest

from ska_mid_dish_manager.models.dish_enums import TrackTableLoadMode
from tests.utils import generate_track_table, remove_subscriptions, setup_subscriptions


@pytest.mark.acceptance
def test_reset_track_table(event_store_class, dish_manager_proxy, ds_device_proxy) -> None:
    """Test ResetTrackTable."""
    end_index_event_store = event_store_class()
    attr_cb_mapping = {
        "trackTableEndIndex": end_index_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    current_pointing = dish_manager_proxy.achievedPointing
    current_az = current_pointing[1]
    current_el = current_pointing[2]
    current_time_tai_s = ds_device_proxy.GetCurrentTAIOffset()
    track_table = generate_track_table(
        num_samples=5,
        current_az=current_az,
        current_el=current_el,
        controller_current_time_tai=current_time_tai_s,
    )

    # load a track table with NEW mode
    dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.NEW
    dish_manager_proxy.programTrackTable = track_table

    # check that the track table is loaded correctly
    expected_end_index = len(track_table) // 3
    end_index_event_store.wait_for_value(expected_end_index)
    assert dish_manager_proxy.trackTableEndIndex == expected_end_index

    dish_manager_proxy.ResetTrackTable()

    # check that the track table is reset to default values
    az, el = 0.0, 50.0
    program_track_table = dish_manager_proxy.programTrackTable
    # Remove all time entries (every third element starting from index 0)
    az_el_only = [v for i, v in enumerate(program_track_table) if i % 3 != 0]
    reset_point = [az, el] * 5
    assert az_el_only == reset_point

    # check that the end index is reset to 1
    expected_end_index = 1
    end_index_event_store.wait_for_value(expected_end_index)
    assert dish_manager_proxy.trackTableEndIndex == expected_end_index
    remove_subscriptions(subscriptions)
