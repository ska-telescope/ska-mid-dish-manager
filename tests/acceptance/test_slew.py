"""Test that Dish Slews to target Azimuth and Elevation."""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode

ELEV_MECHANICAL_LIMIT_MAX = 85.0
AZIM_MECHANICAL_LIMIT_MAX = 360.0


@pytest.mark.acceptance
@pytest.mark.forked
def test_slew_rejected(event_store_class, dish_manager_proxy):
    """Test slew command rejected when not in OPERATE."""
    main_event_store = event_store_class()
    progress_event_store = event_store_class()
    result_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )

    dish_manager_proxy.SetStandbyFPMode()
    main_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=5)

    # Position must be in range but absolute not important
    [[_], [unique_id]] = dish_manager_proxy.Slew([0.0, 50.0])
    events = result_event_store.wait_for_command_id(unique_id, timeout=10)

    assert "Command is not allowed" in events[-1].attr_value.value[1]

    expected_progress_updates = (
        "Slew command rejected for current dishMode. Slew command is allowed for dishMode OPERATE"
    )

    # Wait for the slew command progress update
    progress_event_store.wait_for_progress_update(expected_progress_updates, timeout=6)


@pytest.mark.xfail(
    reason="Transition to dish mode OPERATE only allowed through calling ConfigureBand_x"
)
@pytest.mark.acceptance
@pytest.mark.forked
def test_slew_transition(event_store_class, dish_manager_proxy):
    """Test transition to SLEW."""
    main_event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )
    dish_manager_proxy.SetStandbyFPMode()
    main_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=5)

    # Set mode to Operate to accept Slew command
    dish_manager_proxy.ConfigureBand1(True)
    main_event_store.wait_for_value(DishMode.CONFIG, timeout=10)
    # Await auto transition to OPERATE following band config
    main_event_store.wait_for_value(DishMode.OPERATE, timeout=10)

    achieved_pointing = dish_manager_proxy.achievedPointing
    # Increase by 5 degrees in Azimuth and Elevation unless limits will be hit
    rotation_angle_deg = 5
    slew_azimuth = achieved_pointing[1] + rotation_angle_deg
    slew_elevation = achieved_pointing[2] + rotation_angle_deg
    if slew_azimuth >= AZIM_MECHANICAL_LIMIT_MAX:
        slew_azimuth = achieved_pointing[1] - rotation_angle_deg
    if slew_elevation >= ELEV_MECHANICAL_LIMIT_MAX:
        slew_elevation = achieved_pointing[2] - rotation_angle_deg

    achieved_pointing_event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        "achievedPointing",
        tango.EventType.CHANGE_EVENT,
        achieved_pointing_event_store,
    )
    achieved_pointing_event_store.clear_queue()

    dish_manager_proxy.Slew([slew_azimuth, slew_elevation])

    # wait until no updates
    data_points = achieved_pointing_event_store.get_queue_values(timeout=5)
    # timeout return empty list
    assert data_points
    # returned data is an array of tuple consisting of attribute name and value
    last_az_el = data_points[-1][1]
    # check last az and el received and compare with reference
    achieved_az, achieved_el = last_az_el[1], last_az_el[2]
    assert achieved_az == pytest.approx(slew_azimuth)
    assert achieved_el == pytest.approx(slew_elevation)
