"""Test stow watchdog timeout functionality."""

import time

import pytest
import tango
from ska_control_model import ResultCode

from ska_mid_dish_manager.models.dish_enums import DishMode
from tests.utils import remove_subscriptions, setup_subscriptions

WDT_TIMEOUT = 5.0


@pytest.fixture(autouse=True)
def disable_watchdog(dish_manager_proxy):
    yield
    dish_manager_proxy.watchdogtimeout = 0.0


@pytest.mark.movement
@pytest.mark.acceptance
def test_stow_on_timeout(event_store_class, dish_manager_proxy):
    """Test that expiry of watchdog timer invokes stowing of dish."""
    main_event_store = event_store_class()

    dish_mode_id = dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )

    assert dish_manager_proxy.watchdogtimeout == 0.0

    # Check reset response when watchdog timer is not enabled
    [[result_code], [command_resp]] = dish_manager_proxy.ResetWatchdogTimer()
    assert result_code == ResultCode.FAILED
    assert command_resp == "Watchdog timer is not active."

    # Enable the watchdog timer
    dish_manager_proxy.watchdogtimeout = WDT_TIMEOUT
    assert dish_manager_proxy.watchdogtimeout == WDT_TIMEOUT

    # Wait for the watchdog timer to expire
    time.sleep(WDT_TIMEOUT + 1.0)
    # Wait for the dish to stow
    main_event_store.wait_for_value(DishMode.STOW, 120)
    _, requested_action = dish_manager_proxy.lastCommandedMode
    assert requested_action == "HeartbeatStow"

    dish_manager_proxy.unsubscribe_event(dish_mode_id)


@pytest.mark.movement
@pytest.mark.acceptance
def test_watchdog_reset(event_store_class, dish_manager_proxy):
    """Test that ResetWatchdogTimer resets the watchdog timer."""
    main_event_store = event_store_class()

    dish_mode_id = dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )

    prev_lastwatchdogreset = dish_manager_proxy.lastwatchdogreset
    assert dish_manager_proxy.watchdogtimeout == 0.0

    # Enable the watchdog timer
    dish_manager_proxy.watchdogtimeout = WDT_TIMEOUT
    assert dish_manager_proxy.watchdogtimeout == WDT_TIMEOUT

    WDT_RESET_REPEAT = 5
    for _ in range(WDT_RESET_REPEAT):
        time.sleep(WDT_TIMEOUT / 2)
        # Reset the watchdog timer
        [[result_code], [command_resp]] = dish_manager_proxy.ResetWatchdogTimer()
        curr_lastwatchdogreset = dish_manager_proxy.lastwatchdogreset
        assert prev_lastwatchdogreset != curr_lastwatchdogreset
        assert result_code == ResultCode.OK
        assert command_resp == f"Watchdog timer reset at {curr_lastwatchdogreset}s"
        prev_lastwatchdogreset = curr_lastwatchdogreset

    # Check that watchdog expires after not being reset
    time.sleep(WDT_TIMEOUT + 1.0)

    # Wait for the dish to stow
    main_event_store.wait_for_value(DishMode.STOW, 120)
    _, requested_action = dish_manager_proxy.lastCommandedMode
    assert requested_action == "HeartbeatStow"

    dish_manager_proxy.unsubscribe_event(dish_mode_id)


@pytest.mark.movement
@pytest.mark.acceptance
@pytest.mark.parametrize("disable_timeout", [0.0, -1.0])
def test_disable_watchdog(event_store_class, dish_manager_proxy, disable_timeout):
    """Test that disabling the watchdog timer works."""
    main_event_store = event_store_class()

    dish_mode_id = dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )

    prev_lastwatchdogreset = dish_manager_proxy.lastwatchdogreset
    assert dish_manager_proxy.watchdogtimeout == 0.0

    # Enable the watchdog timer
    dish_manager_proxy.watchdogtimeout = WDT_TIMEOUT
    assert dish_manager_proxy.watchdogtimeout == WDT_TIMEOUT
    time.sleep(WDT_TIMEOUT / 2)

    # Disable the watchdog timer
    dish_manager_proxy.watchdogtimeout = disable_timeout
    assert dish_manager_proxy.watchdogtimeout == disable_timeout
    assert dish_manager_proxy.lastwatchdogreset == prev_lastwatchdogreset

    # Check reset response when watchdog timer is not enabled
    [[result_code], [command_resp]] = dish_manager_proxy.ResetWatchdogTimer()
    assert result_code == ResultCode.FAILED
    assert command_resp == "Watchdog timer is not active."

    # Check that dish does not stow when watchdog is disabled
    with pytest.raises(RuntimeError):
        main_event_store.wait_for_value(DishMode.STOW, 60)

    dish_manager_proxy.unsubscribe_event(dish_mode_id)


@pytest.mark.movement
@pytest.mark.acceptance
def test_watchdog_repeat_stow_without_reset(event_store_class, dish_manager_proxy):
    """Test that the watchdog timer can repeatedly stow the dish without reset."""
    main_event_store = event_store_class()

    dish_mode_id = dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )

    # Enable the watchdog timer
    dish_manager_proxy.watchdogtimeout = WDT_TIMEOUT
    assert dish_manager_proxy.watchdogtimeout == WDT_TIMEOUT

    # Wait for the watchdog timer to expire and stow the dish
    time.sleep(WDT_TIMEOUT + 1.0)
    main_event_store.wait_for_value(DishMode.UNKNOWN, 10)

    # Wait for the dish to stow
    main_event_store.wait_for_value(DishMode.STOW, 120)
    _, requested_action = dish_manager_proxy.lastCommandedMode
    assert requested_action == "HeartbeatStow"

    for _ in range(5):
        dish_manager_proxy.SetStandbyLPMode()
        main_event_store.wait_for_value(DishMode.STANDBY_LP, 5)

        # Check that the watchdog timer is still enabled and will stow again
        time.sleep(WDT_TIMEOUT + 1.0)
        main_event_store.wait_for_value(DishMode.STOW, 20)
        _, requested_action = dish_manager_proxy.lastCommandedMode
        assert requested_action == "HeartbeatStow"

    dish_manager_proxy.unsubscribe_event(dish_mode_id)


@pytest.mark.movement
@pytest.mark.acceptance
def test_attributes_pushed(event_store_class, dish_manager_proxy):
    """Test watchdog attributes are pushed."""
    main_event_store = event_store_class()
    reset_event_store = event_store_class()
    timeout_event_store = event_store_class()
    archive_event_store = event_store_class()

    change_evt_cb_mapping = {
        "dishMode": main_event_store,
        "lastwatchdogreset": reset_event_store,
        "watchdogtimeout": timeout_event_store,
    }
    change_event_subs = setup_subscriptions(dish_manager_proxy, change_evt_cb_mapping)

    archive_evt_cb_mapping = {
        "lastwatchdogreset": archive_event_store,
        "watchdogtimeout": archive_event_store,
    }
    archive_event_subs = setup_subscriptions(
        dish_manager_proxy, archive_evt_cb_mapping, tango.EventType.ARCHIVE_EVENT
    )

    assert dish_manager_proxy.watchdogtimeout == 0.0

    # Enable the watchdog timer
    dish_manager_proxy.watchdogtimeout = WDT_TIMEOUT

    # Check that the watchdogtimeout attribute is pushed
    timeout_event_store.wait_for_value(WDT_TIMEOUT)
    archive_event_store.wait_for_value(WDT_TIMEOUT)

    time.sleep(WDT_TIMEOUT / 2)
    [[result_code], [command_resp]] = dish_manager_proxy.ResetWatchdogTimer()
    assert result_code == ResultCode.OK
    # expected string "Watchdog timer reset at {reset timestamp}s"
    timestamp = float(command_resp.split("at ")[1].strip().removesuffix("s"))
    reset_event_store.wait_for_value(timestamp)
    archive_event_store.wait_for_value(timestamp)

    remove_subscriptions(change_event_subs)
    remove_subscriptions(archive_event_subs)
