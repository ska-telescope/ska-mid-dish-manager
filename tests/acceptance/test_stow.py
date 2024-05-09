"""Test that DS goes into STOW and dishManager reports it"""
import pytest
import tango
from ska_control_model import ResultCode

from ska_mid_dish_manager.models.dish_enums import DishMode, DSOperatingMode


# pylint: disable=too-many-locals,unused-argument
@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_stow_transition(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
    ds_device_proxy,
    spf_device_proxy,
    clear_lrc_in_queue,
):
    """Test transition to STOW"""
    main_event_store = event_store_class()
    ds_event_store = event_store_class()

    # # check no LRC queued
    # clear_lrc_in_queue.clear()
    # assert len(dish_manager_proxy.longrunningcommandidsinqueue) == 0

    # Halt StandbyFp transition to check Stow is executed on DS despite dish manager waiting
    spf_device_proxy.skipAttributeUpdates = True

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )
    main_event_store.clear_queue()

    dish_manager_proxy.SetStandbyFPMode()
    # expect error after timeout
    with pytest.raises(RuntimeError):
        main_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=5)

    # check for LRC queued
    assert len(dish_manager_proxy.longrunningcommandidsinqueue) != 0

    # Call dish mode while LRC in progress
    ds_device_proxy.subscribe_event(
        "operatingMode",
        tango.EventType.CHANGE_EVENT,
        ds_event_store,
    )
    ds_event_store.clear_queue()
    dish_manager_proxy.SetStowMode()
    [[result_code], [_]] = dish_manager_proxy.SetStowMode()
    assert ResultCode(result_code) == ResultCode.OK

    assert ds_event_store.wait_for_value(DSOperatingMode.STOW, timeout=5)

    # # check no LRC queued
    # clear_lrc_in_queue.clear()
    # assert len(dish_manager_proxy.longrunningcommandidsinqueue) == 0
