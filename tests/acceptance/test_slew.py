"""Test that Dish Slews to target Azimuth and Elevation"""
import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode

ELEV_MECHANICAL_LIMIT_MAX = 85.0
AZIM_MECHANICAL_LIMIT_MAX = 360.0


# pylint: disable=too-many-locals,unused-argument
@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_slew_transition(event_store_class, dish_manager_proxy):
    """Test transition to SLEW"""
    main_event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )
    main_event_store.clear_queue()
    dish_manager_proxy.SetStandbyFPMode()
    main_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=5)

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
    assert (last_az_el[1:3] == [slew_azimuth, slew_elevation]).all()
