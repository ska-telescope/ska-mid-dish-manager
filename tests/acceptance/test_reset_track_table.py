"""Test ResetTrackTable on dish manager."""

import pytest
import tango


@pytest.mark.acceptance
@pytest.mark.forked
def test_reset_track_table(dish_manager_proxy: tango.DeviceProxy) -> None:
    """Test ResetTrackTable."""
    dish_manager_proxy.ResetTrackTable()

    az, el = 0.0, 50.0
    program_track_table = dish_manager_proxy.programTrackTable
    # Remove all time entries (every third element starting from index 0)
    az_el_only = [v for i, v in enumerate(program_track_table) if i % 3 != 0]
    reset_point = [az, el] * 5

    assert az_el_only == reset_point
