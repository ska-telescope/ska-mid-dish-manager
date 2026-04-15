import random
from datetime import datetime, timezone
from typing import Any

import pytest
import tango
from ska_control_model import ResultCode

from ska_mid_dish_manager.models.dish_enums import DishMode, PointingState


@pytest.mark.acceptance
def test_abort_from_slew(
    dish_manager_proxy: tango.DeviceProxy,
    ds_device_proxy: tango.DeviceProxy,
    event_store_class: Any,
):
    """Test that we stop movement. LRC only report OK after dish has stopped."""
    slew_stop_timestamp = None
    lrc_finished_timestamp = None

    pointing_state_event_store = event_store_class()
    lrcfin_event_store = event_store_class()

    ds_sub_id = ds_device_proxy.subscribe_event(
        "pointingstate", tango.EventType.CHANGE_EVENT, pointing_state_event_store
    )
    pointing_state_event_store.clear_queue()

    dm_sub_id = dish_manager_proxy.subscribe_event(
        "lrcFinished", tango.EventType.CHANGE_EVENT, lrcfin_event_store
    )
    lrcfin_event_store.clear_queue()

    if dish_manager_proxy.dishmode != DishMode.OPERATE:
        dish_manager_proxy.configureband1(True)

    random_az = random.choice(list(range(-50, 50)))
    dish_manager_proxy.slew([random_az, 50])
    pointing_state_event_store.wait_for_value(PointingState.SLEW, timeout=30)

    result_code, command_id = dish_manager_proxy.Abort()
    command_id = command_id[0]
    assert ResultCode(result_code[0]) == ResultCode.QUEUED

    event = pointing_state_event_store.wait_for_value(PointingState.READY, timeout=30)
    slew_stop_timestamp = event.attr_value.time.todatetime()
    slew_stop_timestamp = slew_stop_timestamp.replace(tzinfo=timezone.utc)

    # Wait for the command to finish
    abort_completed_info: tango.EventType.CHANGE_EVENT = lrcfin_event_store.wait_for_lrcvalue(
        command_id
    )
    assert abort_completed_info["result"]
    assert ResultCode(abort_completed_info["result"][0]) == ResultCode.OK
    lrc_finished_timestamp = datetime.fromisoformat(abort_completed_info["finished_time"])

    # Assert that the LRC finished after the slew stopped
    err_message = (
        f"The LRC finished [{lrc_finished_timestamp}] "
        f"before the dish stopped [{slew_stop_timestamp}]"
    )

    assert lrc_finished_timestamp > slew_stop_timestamp, err_message

    ds_device_proxy.unsubscribe_event(ds_sub_id)
    dish_manager_proxy.unsubscribe_event(dm_sub_id)


@pytest.mark.acceptance
def test_abort_from_non_slew(
    dish_manager_proxy: tango.DeviceProxy,
    ds_device_proxy: tango.DeviceProxy,
    event_store_class: Any,
):
    """Test that Abort returns OK, when dish is standing still."""
    pointing_state_event_store = event_store_class()
    lrcfin_event_store = event_store_class()

    ds_sub_id = ds_device_proxy.subscribe_event(
        "pointingstate", tango.EventType.CHANGE_EVENT, pointing_state_event_store
    )
    pointing_state_event_store.wait_for_value(PointingState.READY)

    dm_sub_id = dish_manager_proxy.subscribe_event(
        "lrcFinished", tango.EventType.CHANGE_EVENT, lrcfin_event_store
    )
    lrcfin_event_store.clear_queue()

    if dish_manager_proxy.dishmode != DishMode.OPERATE:
        dish_manager_proxy.configureband1(True)

    result_code, command_id = dish_manager_proxy.Abort()

    command_id = command_id[0]
    assert ResultCode(result_code[0]) == ResultCode.QUEUED, [
        ResultCode(result_code[0]),
        command_id,
    ]

    # Wait for the command to finish
    abort_completed_info: tango.EventType.CHANGE_EVENT = lrcfin_event_store.wait_for_lrcvalue(
        command_id
    )
    assert abort_completed_info["result"]
    assert ResultCode(abort_completed_info["result"][0]) == ResultCode.OK, abort_completed_info

    ds_device_proxy.unsubscribe_event(ds_sub_id)
    dish_manager_proxy.unsubscribe_event(dm_sub_id)
