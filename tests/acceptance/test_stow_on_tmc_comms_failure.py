"""Test Dish.LMC stows the dish structure on TMC communication failure."""

import time

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode, PointingState


# pylint: disable=too-many-locals,unused-argument,too-many-arguments
@pytest.mark.acceptance
@pytest.mark.forked
def test_dish_lmc_stows_on_tmc_comms_failure(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
):
    """Test Dish.LMC stows the dish structure on TMC communication failure"""
    main_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )

    current_dish_mode = dish_manager_proxy.dishMode

    try:
        # set the stow timeout to 5sec
        dish_manager_proxy.tmcHeartbeatStowTimeout = 5

        assert dish_manager_proxy.tmcHeartbeatStowTimeout == 5

        # wait 6 sec, sending a heartbeat once at 3sec
        time.sleep(3)
        dish_manager_proxy.TMCHeartbeat()
        time.sleep(3)

        # assert that nothing happened on the dish since the heartbeat was within the stow timeout
        assert dish_manager_proxy.pointingState == PointingState.READY
        assert dish_manager_proxy.dishMode == current_dish_mode

        # wait for the timeout to elapse
        time.sleep(5)

        # assert that the dish stows
        main_event_store.wait_for_value(DishMode.STOW, timeout=10)
    finally:
        # clean up for other tests
        dish_manager_proxy.tmcHeartbeatStowTimeout = 0
