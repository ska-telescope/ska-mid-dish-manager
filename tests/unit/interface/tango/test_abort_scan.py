"""Unit tests for AbortScan command."""

import logging
from unittest.mock import Mock, patch

import pytest
import tango
from ska_control_model import ResultCode, TaskStatus

from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    PointingState,
    SPFOperatingMode,
    SPFRxOperatingMode,
)
from ska_mid_dish_manager.utils.ska_epoch_to_tai import get_current_tai_timestamp_from_unix_time


@pytest.mark.unit
@pytest.mark.forked
def test_abort_does_not_run_full_sequence_in_maintenance_dishmode(
    caplog, dish_manager_resources, event_store_class
):
    """Verify Abort is rejected when DishMode is MAINTENANCE."""
    device_proxy, dish_manager_cm = dish_manager_resources
    caplog.set_level(logging.DEBUG, logger=dish_manager_cm.logger.name)

    dish_mode_event_store = event_store_class()

    device_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )

    dish_manager_cm._update_component_state(dishmode=DishMode.MAINTENANCE)
    dish_mode_event_store.wait_for_value(DishMode.MAINTENANCE)
    assert device_proxy.dishMode == DishMode.MAINTENANCE

    device_proxy.AbortScan()
    assert "Dish is in MAINTENANCE mode: abort will only cancel LRCs" in caplog.text
    assert "Abort completed OK" in str(device_proxy.lrcfinished)

    with patch.object(dish_manager_cm, "submit_task") as patched_submit:
        device_proxy.AbortScan()
        assert not patched_submit.called


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "pointing_state",
    [
        PointingState.SLEW,
        PointingState.TRACK,
    ],
)
def test_abort_during_dish_movement(dish_manager_resources, event_store_class, pointing_state):
    """Verify Abort executes the abort sequence."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]
    spfrx_cm = dish_manager_cm.sub_component_managers["SPFRX"]

    # update the execute_command mock to return IN_PROGRESS and a timestamp
    ds_cm.execute_command = Mock(return_value=(TaskStatus.IN_PROGRESS, 1234567890.0))

    dish_mode_event_store = event_store_class()
    lrcfinished_event_store = event_store_class()

    device_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )

    device_proxy.subscribe_event(
        "lrcfinished",
        tango.EventType.CHANGE_EVENT,
        lrcfinished_event_store,
    )

    # Force dishManager dishMode to go to OPERATE
    ds_cm._update_component_state(operatingmode=DSOperatingMode.POINT)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.OPERATE)
    dish_mode_event_store.wait_for_value(DishMode.OPERATE)

    # tracktable will be reset when the dish is tracking. this will make another call to
    # DS to fetch a tai calculation. just replace that object to use the manual approach
    if pointing_state == PointingState.TRACK:
        dish_manager_cm.get_current_tai_offset_from_dsc_with_manual_fallback = (
            get_current_tai_timestamp_from_unix_time
        )
        # mock the reply from ds to load a track table (happens during the table reset)
        mock_response = Mock()
        mock_response.return_value = ResultCode.OK, ""
        dish_manager_cm.track_load_table = mock_response

    # update the pointingState to simulate a dish movement
    ds_cm._update_component_state(pointingstate=pointing_state)

    # Abort the LRC
    [[_], [command_id]] = device_proxy.AbortScan()
    ds_cm._update_component_state(
        **{
            "pointingstate": PointingState.READY,
        }
    )

    details = lrcfinished_event_store.wait_for_lrcvalue(key="uid", value=command_id, timeout=30)
    assert details["result"][0] == ResultCode.OK
    assert details["result"][1] == "Abort LRC Tasks completed."


@pytest.mark.unit
@pytest.mark.forked
def test_abort_fails_on_dsc_error(dish_manager_resources, event_store_class, caplog):
    """Verify Abort fails."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]
    spfrx_cm = dish_manager_cm.sub_component_managers["SPFRX"]

    dish_mode_event_store = event_store_class()
    lrcfinished_event_store = event_store_class()

    device_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )

    device_proxy.subscribe_event(
        "lrcfinished",
        tango.EventType.CHANGE_EVENT,
        lrcfinished_event_store,
    )

    # Force dishManager dishMode to go to OPERATE
    ds_cm._update_component_state(operatingmode=DSOperatingMode.POINT)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.OPERATE)
    dish_mode_event_store.wait_for_value(DishMode.OPERATE)

    with patch.object(ds_cm, "execute_command", side_effect=Exception("Dish Error")):
        [[_], [command_id]] = device_proxy.AbortScan()

        details = lrcfinished_event_store.wait_for_lrcvalue(
            key="uid", value=command_id, timeout=30
        )
        assert details["result"][0] == ResultCode.FAILED
        assert details["result"][1] == "Abort LRC Tasks failed"
    assert "Traceback" in caplog.text
    assert "Dish Error" in caplog.text
