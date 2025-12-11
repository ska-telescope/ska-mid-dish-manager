"""Test that Dish Slews to target Azimuth and Elevation."""

import pytest

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


@pytest.mark.acceptance
def test_slew_outside_bounds_fails(event_store_class, dish_manager_proxy):
    """Test that when given out of bounds azel values, dish manager rejects and returns error."""
    result_store = event_store_class()
    status_store = event_store_class()

    subscriptions = setup_subscriptions(
        dish_manager_proxy,
        {
            "longRunningCommandResult": result_store,
            "longRunningCommandStatus": status_store,
        },
    )

    [[_], [cmd_id]] = dish_manager_proxy.Slew([100, 91])

    events = result_store.wait_for_command_id(cmd_id, timeout=10)
    final_status = events[-1].attr_value.value

    _, status_msg = final_status

    assert "FAILED" in status_msg.upper()
    assert "REJECT" in status_msg.upper()

    statuses = status_store.values_for_command_id(cmd_id)
    assert "STAGING" not in statuses

    queue = dish_manager_proxy.longRunningCommandStatus
    ids_in_queue = [queue[i] for i in range(0, len(queue), 2)]
    assert cmd_id not in ids_in_queue

    remove_subscriptions(subscriptions)


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
