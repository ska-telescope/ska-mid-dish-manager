import random
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
    pointing_state_event_store = event_store_class()
    lrcfin_event_store = event_store_class()
    dish_mode_store = event_store_class()

    dm_mode_sub_id = dish_manager_proxy.subscribe_event(
        "dishmode", tango.EventType.CHANGE_EVENT, dish_mode_store
    )

    ds_sub_id = ds_device_proxy.subscribe_event(
        "pointingstate", tango.EventType.CHANGE_EVENT, pointing_state_event_store
    )
    pointing_state_event_store.clear_queue()

    dm_sub_id = dish_manager_proxy.subscribe_event(
        "lrcFinished", tango.EventType.CHANGE_EVENT, lrcfin_event_store
    )
    lrcfin_event_store.clear_queue()

    dish_manager_proxy.configureband1(True)
    dish_mode_store.wait_for_value(DishMode.OPERATE, timeout=300)

    assert dish_manager_proxy.dishmode == DishMode.OPERATE

    random_az = random.choice(list(range(-50, 50)))
    dish_manager_proxy.slew([random_az, 50])
    pointing_state_event_store.wait_for_value(PointingState.SLEW, timeout=30)

    result_code, command_id = dish_manager_proxy.Abort()
    command_id = command_id[0]
    assert ResultCode(result_code[0]) == ResultCode.QUEUED

    pointing_state_event_store.wait_for_value(PointingState.READY, timeout=300)

    # Wait for the command to finish
    abort_completed_info: tango.EventType.CHANGE_EVENT = lrcfin_event_store.wait_for_lrcvalue(
        command_id
    )
    assert abort_completed_info["result"]
    assert ResultCode(abort_completed_info["result"][0]) == ResultCode.OK

    ds_device_proxy.unsubscribe_event(ds_sub_id)
    dish_manager_proxy.unsubscribe_event(dm_sub_id)
    dish_manager_proxy.unsubscribe_event(dm_mode_sub_id)


@pytest.mark.acceptance
def test_abort_from_non_slew(
    reset_dish_to_standby,
    dish_manager_proxy: tango.DeviceProxy,
    ds_device_proxy: tango.DeviceProxy,
    event_store_class: Any,
):
    """Test that Abort returns OK, when dish is standing still."""
    pointing_state_event_store = event_store_class()
    lrcfin_event_store = event_store_class()
    dish_mode_store = event_store_class()

    dm_mode_sub_id = dish_manager_proxy.subscribe_event(
        "dishmode", tango.EventType.CHANGE_EVENT, dish_mode_store
    )
    ds_sub_id = ds_device_proxy.subscribe_event(
        "pointingstate", tango.EventType.CHANGE_EVENT, pointing_state_event_store
    )
    dm_sub_id = dish_manager_proxy.subscribe_event(
        "lrcFinished", tango.EventType.CHANGE_EVENT, lrcfin_event_store
    )

    dish_manager_proxy.configureband1(True)
    dish_mode_store.wait_for_value(DishMode.OPERATE, timeout=300)

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
    dish_manager_proxy.unsubscribe_event(dm_mode_sub_id)


@pytest.mark.acceptance
def test_abort_from_maintenance(
    reset_dish_to_standby,
    dish_manager_proxy: tango.DeviceProxy,
    event_store_class: Any,
):
    """Test Abort from maintenance."""
    dish_mode_store = event_store_class()
    lrcfin_event_store = event_store_class()

    dm_sub_id = dish_manager_proxy.subscribe_event(
        "dishmode", tango.EventType.CHANGE_EVENT, dish_mode_store
    )

    dm_sub_id = dish_manager_proxy.subscribe_event(
        "lrcFinished", tango.EventType.CHANGE_EVENT, lrcfin_event_store
    )
    lrcfin_event_store.clear_queue()

    dish_manager_proxy.setmaintenancemode()

    dish_mode_store.wait_for_value(DishMode.MAINTENANCE, timeout=300)

    _, command_id = dish_manager_proxy.Abort()
    command_id = command_id[0]
    # Wait for the command to finish
    tango.EventType.CHANGE_EVENT = lrcfin_event_store.wait_for_lrcvalue(command_id, timeout=5)

    dish_manager_proxy.unsubscribe_event(dm_sub_id)
