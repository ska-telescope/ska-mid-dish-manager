"""Tests dish manager ResetTrackTable command handler."""

from unittest.mock import Mock

import pytest
from ska_control_model import ResultCode

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager


@pytest.mark.unit
def test_reset_track_table_handler(
    component_manager: DishManagerComponentManager,
) -> None:
    """Verify behaviour of ResetTrackTable command handler.

    :param component_manager: the component manager under test
    """
    timestamp = 1234567890.0
    component_manager.get_current_tai_offset_from_dsc_with_manual_fallback = Mock(
        return_value=timestamp
    )
    result_code, reset_point = component_manager.reset_track_table()
    # reset_track_table adds a 5s lead time
    expected_reset_point = [timestamp + 5, 0.0, 50.0] * 5

    assert (result_code, reset_point) == (ResultCode.OK, expected_reset_point)
