"""Unit tests for the unhappy paths of the TrackLoadTable command."""

import pytest
import tango
from mock import Mock, patch
from ska_control_model import ResultCode


# pylint: disable=missing-function-docstring, protected-access
@pytest.mark.unit
@pytest.mark.forked
def test_track_load_table_unhappy_paths(
    dish_manager_resources,
):
    device_proxy, dish_manager_cm = dish_manager_resources

    # Mock out the `track_load_table` call in the `programTrackTable` since this test focuses on
    # the behavior of `get_current_tai_offset_from_dsc_with_manual_fallback`
    mock_track_load_table = Mock()
    mock_track_load_table.return_value = ResultCode.OK, ""
    dish_manager_cm.track_load_table = mock_track_load_table

    # Test that programTrackTable still works if the `execute_command` of
    # `get_current_tai_offset_from_dsc_with_manual_fallback` raises a DevFailed error
    with patch.object(
        dish_manager_cm.sub_component_managers["DS"], "execute_command"
    ) as mock_execute_command:
        mock_execute_command.side_effect = tango.DevFailed("Command failed")
        dish_manager_cm.sub_component_managers["DS"].execute_command = mock_execute_command

        test_table = [1, 2, 3]
        device_proxy.programTrackTable = test_table
        assert (device_proxy.programTrackTable == test_table).all()

    # Test that programTrackTable still works if the `execute_command` of
    # `get_current_tai_offset_from_dsc_with_manual_fallback` raises a ConnectionError
    with patch.object(
        dish_manager_cm.sub_component_managers["DS"], "execute_command"
    ) as mock_execute_command:
        mock_execute_command.side_effect = ConnectionError("Command failed")
        dish_manager_cm.sub_component_managers["DS"].execute_command = mock_execute_command

        test_table = [4, 5, 6]
        device_proxy.programTrackTable = test_table
        assert (device_proxy.programTrackTable == test_table).all()
