"""Test that Dish Slews to target Azimuth and Elevation."""

import pytest
from ska_control_model import ResultCode

from ska_mid_dish_manager.models.dish_enums import DishMode
from tests.utils import remove_subscriptions, setup_subscriptions

ELEV_MECHANICAL_LIMIT_MAX = 85.0
AZIM_MECHANICAL_LIMIT_MAX = 360.0
POINTING_TOLERANCE_DEG = 0.1


@pytest.mark.acceptance
def test_slew_rejected(event_store_class, dish_manager_proxy):
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


@pytest.mark.blah
def test_slew_outside_bounds_rejected(event_store_class, ds_device_proxy):
    """Out of bounds azel is rejected immediately and does not start LRC."""
    [[result_code], [unique_id]] = ds_device_proxy.Slew([100, 91])

    lrc_status_event_store = event_store_class()

    ds_device_proxy.subscribe_event(
        "longRunningCommandStatus",
        tango.EventType.CHANGE_EVENT,
        lrc_status_event_store
    )

    assert lrc_status_event_store.wait_for_value((unique_id, "REJECTED"))

    assert result_code == ResultCode.REJECTED


@pytest.mark.blah
def test_slew_extra_arg_fails(event_store_class, dish_manager_proxy):
    """Test that when given three arguments instead of two, the command is rejected."""
    [[result_code], [unique_id]] = dish_manager_proxy.Slew([100,100,100])

    lrc_status_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "longRunningCommandStatus",
        tango.EventType.CHANGE_EVENT,
        lrc_status_event_store
    )

    assert lrc_status_event_store.wait_for_value((unique_id, "REJECTED"))
    assert result_code == ResultCode.REJECTED


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
