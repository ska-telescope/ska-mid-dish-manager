"""Test Abort."""

import pytest
from ska_mid_dish_ds_manager.models.dish_enums import (
    PointingState,
    TrackTableLoadMode,
)
from ska_mid_dish_simulators.sim_enums import (
    Band,
)

from ska_mid_dish_manager.models.constants import (
    MAX_AZIMUTH,
    MAX_ELEVATION_SCIENCE,
    MIN_AZIMUTH,
    MIN_ELEVATION_SCIENCE,
    STOW_ELEVATION_DEGREES,
)
from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
)
from tests.utils import calculate_slew_target, remove_subscriptions, setup_subscriptions


@pytest.mark.acceptance
def test_abort_commands(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
    spf_device_proxy,
    toggle_skip_attributes,
):
    """Test Abort aborts the executing long running command."""
    dish_mode_event_store = event_store_class()
    status_event_store = event_store_class()
    result_event_store = event_store_class()
    cmds_in_queue_store = event_store_class()

    attr_cb_mapping = {
        "dishMode": dish_mode_event_store,
        "longRunningCommandResult": result_event_store,
        "longRunningCommandsInQueue": cmds_in_queue_store,
        "Status": status_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    # Attempt to configure which will take SPF to Operate mode,
    # this wont happen because skipAttributeUpdates was set to True
    dish_manager_proxy.ConfigureBand1(True)

    # Check that Dish Manager is waiting to transition
    status_event_store.wait_for_progress_update("Awaiting configuredband change to B1")
    # Check that the Dish Manager did not transition
    dish_mode_event_store.wait_for_value(DishMode.UNKNOWN, timeout=10)
    assert dish_manager_proxy.dishMode == DishMode.UNKNOWN

    # enable spf to send attribute updates
    spf_device_proxy.skipAttributeUpdates = False

    # Abort the LRC
    [[_], [unique_id]] = dish_manager_proxy.Abort()
    # Confirm Dish Manager aborted the request on the Configure action
    result_event_store.wait_for_command_result(unique_id, '[0, "Abort completed OK"]', timeout=30)
    status_event_store.wait_for_progress_update("SetOperateMode aborted", timeout=30)

    # Confirm that abort finished and the queue is cleared
    cmds_in_queue_store.wait_for_value((), timeout=30)

    # Check that the Dish Manager transitioned to FP as part of the Abort sequence
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=30)
    assert dish_manager_proxy.dishMode == DishMode.STANDBY_FP

    remove_subscriptions(subscriptions)


@pytest.fixture
def track_a_sample(
    event_store_class,
    dish_manager_proxy,
    ds_device_proxy,
):
    """Execute a track command to slew the dish to a new position."""
    main_event_store = event_store_class()
    band_event_store = event_store_class()
    result_event_store = event_store_class()

    attr_cb_mapping = {
        "dishMode": main_event_store,
        "pointingState": main_event_store,
        "longRunningCommandResult": result_event_store,
        "configuredBand": band_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    dish_manager_proxy.ConfigureBand1(True)
    band_event_store.wait_for_value(Band.B1, timeout=30)
    main_event_store.wait_for_value(DishMode.OPERATE, timeout=30, proxy=dish_manager_proxy)

    # Load a track table
    current_az, current_el = dish_manager_proxy.achievedPointing[1:]
    current_time_tai_s = ds_device_proxy.GetCurrentTAIOffset()

    # Use constant azimuth and elevation to track for simplicity
    reference_az = current_az
    reference_el = current_el
    # if near limits, adjust to be well within limits
    if current_el >= MAX_ELEVATION_SCIENCE:
        reference_el = current_el - 10.0
    if current_el <= MIN_ELEVATION_SCIENCE:
        reference_el = current_el + 10.0
    if current_az >= MAX_AZIMUTH:
        reference_az = current_az - 10.0
    if current_az <= MIN_AZIMUTH:
        reference_az = current_az + 10.0

    # create a long track table with last three reference positions the same
    track_table = [
        current_time_tai_s + 3,
        reference_az,
        reference_el,
        current_time_tai_s + 5,
        reference_az,
        reference_el,
        current_time_tai_s + 7,
        reference_az,
        reference_el,
        current_time_tai_s + 20,
        reference_az,
        reference_el,
        current_time_tai_s + 30,
        reference_az,
        reference_el,
    ]

    dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.NEW
    dish_manager_proxy.programTrackTable = track_table

    [[_], [unique_id]] = dish_manager_proxy.Track()
    # Wait for the track command to return
    result_event_store.wait_for_command_id(unique_id, timeout=30)
    main_event_store.wait_for_value(PointingState.TRACK, timeout=30)

    remove_subscriptions(subscriptions)
    yield


@pytest.mark.acceptance
def test_abort_commands_during_track(
    monitor_tango_servers,
    track_a_sample,
    event_store_class,
    dish_manager_proxy,
):
    """Test that Abort aborts the executing track command."""
    result_event_store = event_store_class()
    main_event_store = event_store_class()

    attr_cb_mapping = {
        "dishMode": main_event_store,
        "longRunningCommandResult": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    # Call Abort on DishManager
    [[_], [unique_id]] = dish_manager_proxy.Abort()
    result_event_store.wait_for_command_result(unique_id, '[0, "Abort completed OK"]', timeout=30)

    main_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=10)
    assert dish_manager_proxy.dishMode == DishMode.STANDBY_FP

    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
def test_abort_commands_during_slew(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
):
    """Test that Abort aborts the executing slew command."""
    result_event_store = event_store_class()
    main_event_store = event_store_class()

    attr_cb_mapping = {
        "dishMode": main_event_store,
        "pointingState": main_event_store,
        "longRunningCommandResult": result_event_store,
        "configuredBand": main_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    dish_manager_proxy.ConfigureBand1(True)
    main_event_store.wait_for_value(Band.B1, timeout=30)

    # Slew the dish
    current_az, current_el = dish_manager_proxy.achievedPointing[1:]
    requested_az, requested_el = calculate_slew_target(current_az, current_el, 30.0, 15.0)
    dish_manager_proxy.Slew([requested_az, requested_el])
    main_event_store.wait_for_value(PointingState.SLEW, timeout=10)

    # Call Abort on DishManager
    [[_], [unique_id]] = dish_manager_proxy.Abort()
    result_event_store.wait_for_command_result(unique_id, '[0, "Abort completed OK"]', timeout=30)

    main_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=30)
    # Check that the dish is in standby FP mode
    assert dish_manager_proxy.dishMode == DishMode.STANDBY_FP
    # Check that the dish did not slew to the requested position
    achieved_az, achieved_el = dish_manager_proxy.achievedPointing[1:]
    assert achieved_az != pytest.approx(requested_az)
    assert achieved_el != pytest.approx(requested_el)

    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
def test_abort_commands_during_stow(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
    ds_device_proxy,
):
    """Test that Abort aborts the executing stow command."""
    result_event_store = event_store_class()
    main_event_store = event_store_class()

    attr_cb_mapping = {
        "dishMode": main_event_store,
        "pointingState": main_event_store,
        "longRunningCommandResult": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    # If already in stow position, move to different position
    # so that effort of aborting stow can be observed
    current_pointing = dish_manager_proxy.achievedPointing
    desired_el = 70.0
    if current_pointing[2] == pytest.approx(STOW_ELEVATION_DEGREES):
        ds_device_proxy.Slew([current_pointing[1], desired_el])
        main_event_store.clear_queue()
        main_event_store.wait_for_value(PointingState.READY, timeout=30)

    # Stow the dish
    dish_manager_proxy.SetStowMode()
    main_event_store.wait_for_value(PointingState.SLEW, timeout=10)

    # Call Abort on DishManager
    [[_], [unique_id]] = dish_manager_proxy.Abort()
    result_event_store.wait_for_command_result(unique_id, '[0, "Abort completed OK"]', timeout=30)

    main_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=30)
    # Check that the dish is in standby FP mode
    assert dish_manager_proxy.dishMode == DishMode.STANDBY_FP
    # Check that the dish did not slew to the stow position
    stow_el_position = STOW_ELEVATION_DEGREES
    achieved_el = dish_manager_proxy.achievedPointing[2]
    assert achieved_el != pytest.approx(stow_el_position)

    remove_subscriptions(subscriptions)
