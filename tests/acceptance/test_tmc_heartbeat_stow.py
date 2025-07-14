"""Test the TMC heartbeat stow."""

import time
from datetime import datetime

import pytest
import tango
from ska_control_model import ResultCode

from ska_mid_dish_manager.models.dish_enums import DishMode


@pytest.mark.acceptance
@pytest.mark.forked
def test_tmc_stow_heartbeat(event_store_class, dish_manager_proxy):
    """Test that a lapse in interval invokes STOW."""
    main_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )

    dish_manager_proxy.SetStandbyFPMode()
    assert dish_manager_proxy.read_attribute("tmcLastHeartbeat").value == 0.0
    assert dish_manager_proxy.read_attribute("tmcHeartbeatInterval").value == 0.0

    # Set the interval
    dish_manager_proxy.write_attribute("tmcHeartbeatInterval", 4.0)
    assert dish_manager_proxy.read_attribute("tmcHeartbeatInterval").value == 4.0

    # Start tracking the pings by sending the first heartbeat
    [[result_code], [command_resp]] = dish_manager_proxy.TMCHeartbeat()

    assert command_resp == "TMC heartbeat received at: %s" % (
        datetime.fromtimestamp(dish_manager_proxy.read_attribute("tmcLastHearteat").value)
    )

    assert result_code == ResultCode.OK
    assert dish_manager_proxy.read_attribute("tmcheartbeatinterval").value == 4.0

    # Test that the dish will stow when interval is lapsed
    # Wait for the Dish to STOW
    main_event_store.wait_for_value(DishMode.STOW, 25)

    # Confirm that once the interval has lapsed the tmcLastHeartbeat
    # and tmcHeartbeatInterval attributes are reset.
    assert dish_manager_proxy.read_attribute("tmcHeartbeatInterval").value == 0.0
    assert dish_manager_proxy.read_attribute("tmcLastHeartbeat").value == 0.0


@pytest.mark.acceptance
@pytest.mark.forked
def test_pings_in_stow(event_store_class, dish_manager_proxy):
    """Test pings in STOW mode."""
    main_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )

    dish_manager_proxy.SetStandbyLPMode()
    dish_manager_proxy.SetStowMode()
    main_event_store.wait_for_value(DishMode.STOW, timeout=25)

    assert dish_manager_proxy.read_attribute("tmcLastHeartbeat").value == 0.0
    assert dish_manager_proxy.read_attribute("tmcHeartbeatInterval").value == 0.0

    # Send 5 pings within the interval
    dish_manager_proxy.write_attribute("tmcHeartbeatInterval", 2.0)
    assert dish_manager_proxy.read_attribute("tmcHeartbeatInterval").value == 2.0

    old_heartbeat = 0.0
    new_heartbeat = 0.0

    for i in range(5):
        dish_manager_proxy.TMCHeartbeat()
        if i == 0:
            old_heartbeat = dish_manager_proxy.read_attribute("tmcLastHeartbeat").value
            assert old_heartbeat == dish_manager_proxy.read_attribute("tmcLastHeartbeat").value
        else:
            new_heartbeat = dish_manager_proxy.read_attribute("tmcLastHeartbeat").value
            assert new_heartbeat > old_heartbeat
            old_heartbeat = new_heartbeat
        time.sleep(2)  # Sleep for 2s

    # Stop Dish.LMC from tracking the pings
    dish_manager_proxy.write_attribute("tmcHeartbeatInterval", 0.0)
    assert dish_manager_proxy.read_attribute("tmcHeartbeatInterval").value == 0.0
    assert dish_manager_proxy.read_attribute("tmcLastHeartbeat").value == 0.0
    # Check that the dish is still in STOW mode.
    dish_manager_proxy.read_attribute("dishMode").value = DishMode.STOW

    # Test that when the dishMode is STOW mode and pings exceed the interval the dish
    # remains in STOW mode.
    dish_manager_proxy.write_attribute("tmcHeartbeatInterval", 1.0)
    time.sleep(2)  # Sleep for 2s
    dish_manager_proxy.read_attribute("dishMode").value = DishMode.STOW


@pytest.mark.acceptance
@pytest.mark.forked
def test_tmc_pings_within_interval(event_store_class, dish_manager_proxy):
    """Test successful pings within the prescribed interval."""
    main_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )

    dish_manager_proxy.SetStandbyFPMode()
    assert dish_manager_proxy.read_attribute("tmcLastHeartbeat").value == 0.0
    assert dish_manager_proxy.read_attribute("tmcHeartbeatInterval").value == 0.0

    # Set the interval
    dish_manager_proxy.write_attribute("tmcHeartbeatInterval", 2.0)
    assert dish_manager_proxy.read_attribute("tmcHeartbeatInterval").value == 2.0

    old_heartbeat = 0.0
    new_heartbeat = 0.0

    for i in range(5):
        dish_manager_proxy.TMCHeartbeat()
        if i == 0:
            old_heartbeat = dish_manager_proxy.read_attribute("tmcLastHeartbeat").value
            assert old_heartbeat == dish_manager_proxy.read_attribute("tmcLastHeartbeat").value
        else:
            new_heartbeat = dish_manager_proxy.read_attribute("tmcLastHeartbeat").value
            assert new_heartbeat > old_heartbeat
            old_heartbeat = new_heartbeat
    time.sleep(2)  # Sleep for 2s
    dish_manager_proxy.read_attribute("dishMode").value = DishMode.STANDBY_FP
