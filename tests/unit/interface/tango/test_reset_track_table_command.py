"""Unit tests for the ResetTrackTable command on dish manager."""

from unittest.mock import Mock

import pytest
import tango
from ska_control_model import ResultCode, TaskStatus


@pytest.mark.unit
@pytest.mark.forked
def test_reset_track_table(dish_manager_resources, event_store_class):
    """Test ResetTrackTable."""
    device_proxy, dish_manager_cm = dish_manager_resources
    main_event_store = event_store_class()
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    # update the execute_command mock to return IN_PROGRESS and a timestamp
    timestamp = 1234567890.0
    ds_cm.execute_command = Mock(return_value=(TaskStatus.IN_PROGRESS, timestamp))

    device_proxy.subscribe_event(
        "programTrackTable",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )
    # Clear out the queue to make sure we don't catch old events
    main_event_store.clear_queue()

    az, el = 0.0, 50.0
    reset_point = [timestamp + 5, az, el] * 5
    [[result_code], [message]] = device_proxy.ResetTrackTable()
    main_event_store.wait_for_value(reset_point)

    assert all(device_proxy.programTrackTable == reset_point)
    assert result_code == ResultCode.OK
    assert message == "programTrackTable successfully reset"
