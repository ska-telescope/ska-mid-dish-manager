"""Test that Dish Slews to target Azimuth and Elevation."""

import pytest
import tango
from ska_control_model import ResultCode

from ska_mid_dish_manager.models.dish_enums import DishMode
from tests.utils import remove_subscriptions, setup_subscriptions

ELEV_MECHANICAL_LIMIT_MAX = 85.0
AZIM_MECHANICAL_LIMIT_MAX = 360.0
POINTING_TOLERANCE_DEG = 0.1


@pytest.mark.acceptance
def test_slew_rejected_in_wrong_dish_mode(event_store_class, dish_manager_proxy):
    """Test slew command rejected when not in OPERATE."""
    status_event_store = event_store_class()
    result_event_store = event_store_class()
    attr_cb_mapping = {
        "longRunningCommandResult": result_event_store,
        "Status": status_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    # Position must be in range but absolute not important
    [[_], [unique_id]] = dish_manager_proxy.Slew([0.0, 50.0])
    events = result_event_store.wait_for_command_id(unique_id, timeout=10)

    assert "Command is not allowed" in events[-1].attr_value.value[1]

    expected_progress_updates = (
        "Slew command rejected for current dishMode. Slew command is allowed for dishMode OPERATE"
    )

    # Wait for the slew command progress update
    status_event_store.wait_for_progress_update(expected_progress_updates, timeout=6)
    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
def test_slew_outside_bounds_rejected(event_store_class, dish_manager_proxy, ds_device_proxy):
    """Out of bounds azel is rejected on the dish structure."""
    # set up subscriptions on dish manager
    dish_mode_event_store = event_store_class()
    dm_event_id = dish_manager_proxy.subscribe_event(
        "dishMode", tango.EventType.CHANGE_EVENT, dish_mode_event_store
    )
    dish_mode_event_store.clear_queue()

    # set up subscriptions on dish structure
    ds_lrc_status_event_store = event_store_class()
    ds_event_id = ds_device_proxy.subscribe_event(
        "longRunningCommandStatus",
        tango.EventType.CHANGE_EVENT,
        ds_lrc_status_event_store,
    )
    ds_lrc_status_event_store.clear_queue()

    # Set mode to Operate to accept Slew command
    dish_manager_proxy.ConfigureBand1(True)
    # Await auto transition to OPERATE following band config
    dish_mode_event_store.wait_for_value(DishMode.OPERATE, timeout=30)
    dish_manager_proxy.Slew([100, 91])

    # check that dish structure rejected the command
    lrc_status_events = ds_lrc_status_event_store.get_queue_values()
    # lrc_status_events looks like:
    # [('attr_name', ('unique_id', 'STAGING')), ('attr_name', ('unique_id', 'REJECTED')), ... ]
    # discard the attr_name and join the event values into a single string for easier searching
    # e.g. "('unique_id', 'STAGING')('unique_id', 'REJECTED')"
    lrc_status_events = "".join([str(lrc_status) for _, lrc_status in lrc_status_events])
    assert "Slew', 'REJECTED'" in lrc_status_events

    # clean up subscriptions
    dish_manager_proxy.unsubscribe_event(dm_event_id)
    ds_device_proxy.unsubscribe_event(ds_event_id)


@pytest.mark.acceptance
def test_slew_extra_arg_fails(event_store_class, dish_manager_proxy):
    """Test that when given three arguments instead of two, the command is rejected."""
    lrc_status_event_store = event_store_class()
    subscription_id = dish_manager_proxy.subscribe_event(
        "longRunningCommandStatus", tango.EventType.CHANGE_EVENT, lrc_status_event_store
    )
    lrc_status_event_store.clear_queue()

    [[result_code], [message]] = dish_manager_proxy.Slew([100, 100, 100])
    assert result_code == ResultCode.REJECTED
    assert message == "Expected 2 arguments (az, el) but got 3 arg(s)."
    # Check that the longRunningCommandStatus event shows the command was rejected
    lrc_status_events = lrc_status_event_store.get_queue_values()
    lrc_status_events = "".join([str(event_value) for _, event_value in lrc_status_events])
    assert "Slew', 'REJECTED'" in lrc_status_events

    dish_manager_proxy.unsubscribe_event(subscription_id)


@pytest.mark.acceptance
def test_slew_transition(event_store_class, dish_manager_proxy):
    """Test transition to SLEW."""
    main_event_store = event_store_class()
    achieved_pointing_event_store = event_store_class()
    attr_cb_mapping = {
        "dishMode": main_event_store,
        "achievedPointing": achieved_pointing_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    # Set mode to Operate to accept Slew command
    dish_manager_proxy.ConfigureBand1(True)
    # Await auto transition to OPERATE following band config
    main_event_store.wait_for_value(DishMode.OPERATE, timeout=30)

    achieved_pointing = dish_manager_proxy.achievedPointing
    # Increase by 5 degrees in Azimuth and Elevation unless limits will be hit
    rotation_angle_deg = 5
    slew_azimuth = achieved_pointing[1] + rotation_angle_deg
    slew_elevation = achieved_pointing[2] + rotation_angle_deg
    if slew_azimuth >= AZIM_MECHANICAL_LIMIT_MAX:
        slew_azimuth = achieved_pointing[1] - rotation_angle_deg
    if slew_elevation >= ELEV_MECHANICAL_LIMIT_MAX:
        slew_elevation = achieved_pointing[2] - rotation_angle_deg

    dish_manager_proxy.Slew([slew_azimuth, slew_elevation])

    def target_reached_test(pointing_event_val: list[float]) -> bool:
        """Return whether we got to the target."""
        return pointing_event_val[1] == pytest.approx(
            slew_azimuth, abs=POINTING_TOLERANCE_DEG
        ) and pointing_event_val[2] == pytest.approx(slew_elevation, abs=POINTING_TOLERANCE_DEG)

    achieved_pointing_event_store.wait_for_condition(target_reached_test, timeout=60)

    remove_subscriptions(subscriptions)
