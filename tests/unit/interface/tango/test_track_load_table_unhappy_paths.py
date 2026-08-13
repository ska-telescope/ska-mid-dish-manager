"""Unit tests for the unhappy paths of the TrackLoadTable command."""

from typing import Any

import pytest
from mock import Mock, patch
from ska_control_model import TaskStatus
from tango import DeviceProxy


@pytest.mark.unit
@pytest.mark.forked
def test_track_load_table_unhappy_paths(
    dish_manager_resources: tuple[None | DeviceProxy, Any],
):
    device_proxy, dish_manager_cm = dish_manager_resources
    assert device_proxy is not None
    assert dish_manager_cm is not None

    # Mock out the `track_load_table` call in the `programTrackTable` since this test focuses on
    # the behavior of `get_current_tai_offset_from_dsc_with_manual_fallback`
    mock_track_load_table = Mock()
    mock_track_load_table.return_value = TaskStatus.IN_PROGRESS, ""
    dish_manager_cm.track_load_table = mock_track_load_table

    # Test that programTrackTable still works if the `execute_command` of
    # `get_current_tai_offset_from_dsc_with_manual_fallback` raises a DevFailed error
    with patch.object(  # ty: ignore[unresolved-attribute]
        dish_manager_cm.sub_component_managers["DS"], "execute_command"
    ) as mock_execute_command:
        mock_execute_command.side_effect = KeyError("Command failed")
        dish_manager_cm.sub_component_managers["DS"].execute_command = mock_execute_command

        test_table = [1, 2, 3]
        device_proxy.programTrackTable = test_table
        assert device_proxy.programTrackTable == test_table

    # Test that programTrackTable still works if the `execute_command` of
    # `get_current_tai_offset_from_dsc_with_manual_fallback` raises a ConnectionError
    with patch.object(  # ty: ignore[unresolved-attribute]
        dish_manager_cm.sub_component_managers["DS"], "execute_command"
    ) as mock_execute_command:
        mock_execute_command.side_effect = ConnectionError("Command failed")
        dish_manager_cm.sub_component_managers["DS"].execute_command = mock_execute_command

        test_table = [4, 5, 6]
        device_proxy.programTrackTable = test_table
        assert device_proxy.programTrackTable == test_table

    with patch.object(  # ty: ignore[unresolved-attribute]
        dish_manager_cm.sub_component_managers["DS"], "execute_command"
    ) as mock_execute_command:
        mock_execute_command.return_value = TaskStatus.FAILED, "Command failed"
        dish_manager_cm.sub_component_managers["DS"].execute_command = mock_execute_command

        test_table = [4, 5, 6]
        device_proxy.programTrackTable = test_table
        assert device_proxy.programTrackTable == test_table
