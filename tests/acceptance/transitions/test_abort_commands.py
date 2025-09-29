"""Test AbortCommands."""

import pytest

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
    PointingState,
    TrackTableLoadMode,
)
from tests.utils import calculate_slew_target, remove_subscriptions, setup_subscriptions


@pytest.fixture
def toggle_skip_attributes(event_store_class, spf_device_proxy, dish_manager_proxy):
    """Ensure that attribute updates on spf is restored."""
    dish_manager_proxy.SetStandbyLPMode()
    dish_mode_event_store = event_store_class()
    sub = setup_subscriptions(dish_manager_proxy, {"dishMode": dish_mode_event_store})
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_LP, timeout=20)
    remove_subscriptions(sub)
    # Set a flag on SPF to skip attribute updates.
    # This is useful to ensure that the long running command
    # does not finish executing before AbortCommands is triggered
    spf_device_proxy.skipAttributeUpdates = True
    yield
    spf_device_proxy.skipAttributeUpdates = False


@pytest.mark.acceptance
@pytest.mark.forked
def test_abort_commands(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
    spf_device_proxy,
    toggle_skip_attributes,
):
    """Test AbortCommands aborts the executing long running command."""
    dish_mode_event_store = event_store_class()
    progress_event_store = event_store_class()
    result_event_store = event_store_class()
    cmds_in_queue_store = event_store_class()

    attr_cb_mapping = {
        "dishMode": dish_mode_event_store,
        "longRunningCommandProgress": progress_event_store,
        "longRunningCommandResult": result_event_store,
        "longRunningCommandsInQueue": cmds_in_queue_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    # Transition to FP mode
    [[_], [lp_unique_id]] = dish_manager_proxy.SetStandbyFPMode()

    # Check that Dish Manager is waiting to transition to FP
    progress_event_store.wait_for_progress_update("Awaiting dishmode change to STANDBY_FP")
    # Check that the Dish Manager did not transition to FP
    dish_mode_event_store.wait_for_value(DishMode.UNKNOWN)
    assert dish_manager_proxy.dishMode == DishMode.UNKNOWN

    # enable spf to send attribute updates
    spf_device_proxy.skipAttributeUpdates = False

    # Abort the LRC
    [[_], [abort_unique_id]] = dish_manager_proxy.AbortCommands()
    # Confirm Dish Manager aborted the request on LRC
    result_event_store.wait_for_command_id(lp_unique_id, timeout=30)
    # Abort will execute standbyfp dishmode as part of its abort sequence
    expected_progress_updates = [
        "SetStandbyFPMode Aborted",
        "SetOperateMode called on SPF",
        "SetStandbyFPMode called on DS",
        "Awaiting dishmode change to STANDBY_FP",
        "SetStandbyFPMode completed",
    ]
    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )
    events_string = "".join([str(event.attr_value.value) for event in events])
    # Check that all the expected progress messages appeared
    for message in expected_progress_updates:
        assert message in events_string

    # Confirm that abort finished and the queue is cleared
    result_event_store.wait_for_command_id(abort_unique_id)
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
    progress_event_store = event_store_class()

    attr_cb_mapping = {
        "dishMode": main_event_store,
        "pointingState": main_event_store,
        "longRunningCommandProgress": progress_event_store,
        "longRunningCommandResult": result_event_store,
        "configuredBand": band_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    dish_manager_proxy.ConfigureBand1(True)
    band_event_store.wait_for_value(Band.B1, timeout=30)

    dish_manager_proxy.SetOperateMode()
    main_event_store.wait_for_value(DishMode.OPERATE, timeout=10, proxy=dish_manager_proxy)

    # Load a track table
    current_az, current_el = dish_manager_proxy.achievedPointing[1:]
    current_time_tai_s = ds_device_proxy.GetCurrentTAIOffset()

    # Directions to move values
    az_dir = 1 if current_az < 350 else -1
    el_dir = 1 if current_el < 80 else -1

    # create a long track table with last three reference positions the same
    track_table = [
        current_time_tai_s + 3,
        current_az + 1 * az_dir,
        current_el + 1 * el_dir,
        current_time_tai_s + 5,
        current_az + 2 * az_dir,
        current_el + 2 * el_dir,
        current_time_tai_s + 7,
        current_az + 3 * az_dir,
        current_el + 3 * el_dir,
        current_time_tai_s + 20,
        current_az + 3 * az_dir,
        current_el + 3 * el_dir,
        current_time_tai_s + 30,
        current_az + 3 * az_dir,
        current_el + 3 * el_dir,
    ]

    dish_manager_proxy.trackTableLoadMode = TrackTableLoadMode.NEW
    dish_manager_proxy.programTrackTable = track_table

    [[_], [unique_id]] = dish_manager_proxy.Track()
    result_event_store.wait_for_command_id(unique_id, timeout=8)
    main_event_store.wait_for_value(PointingState.SLEW, timeout=6)
    main_event_store.wait_for_value(PointingState.TRACK, timeout=6)

    expected_progress_update = (
        "Track command has been executed on DS. "
        "Monitor the achievedTargetLock attribute to determine when the dish is on source."
    )

    # Wait for the track command to return
    progress_event_store.wait_for_progress_update(expected_progress_update, timeout=6)
    remove_subscriptions(subscriptions)
    yield


@pytest.mark.acceptance
@pytest.mark.forked
def test_abort_commands_during_track(
    monitor_tango_servers,
    track_a_sample,
    event_store_class,
    dish_manager_proxy,
):
    """Test that AbortCommands aborts the executing track command."""
    result_event_store = event_store_class()
    main_event_store = event_store_class()

    attr_cb_mapping = {
        "dishMode": main_event_store,
        "longRunningCommandResult": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    # Call AbortCommands on DishManager
    [[_], [unique_id]] = dish_manager_proxy.AbortCommands()
    result_event_store.wait_for_command_result(
        unique_id, '[0, "Abort sequence completed"]', timeout=30
    )

    main_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=10)
    assert dish_manager_proxy.dishMode == DishMode.STANDBY_FP

    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
@pytest.mark.forked
def test_abort_commands_during_slew(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
):
    """Test that AbortCommands aborts the executing slew command."""
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

    dish_manager_proxy.SetOperateMode()
    main_event_store.wait_for_value(DishMode.OPERATE, timeout=10, proxy=dish_manager_proxy)

    # Slew the dish
    current_az, current_el = dish_manager_proxy.achievedPointing[1:]
    requested_az, requested_el = calculate_slew_target(current_az, current_el, 30.0, 15.0)
    dish_manager_proxy.Slew([requested_az, requested_el])
    main_event_store.wait_for_value(PointingState.SLEW, timeout=10)

    # Call AbortCommands on DishManager
    [[_], [unique_id]] = dish_manager_proxy.AbortCommands()
    result_event_store.wait_for_command_result(
        unique_id, '[0, "Abort sequence completed"]', timeout=30
    )

    main_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=30)
    # Check that the dish is in standby FP mode
    assert dish_manager_proxy.dishMode == DishMode.STANDBY_FP
    # Check that the dish did not slew to the requested position
    achieved_az, achieved_el = dish_manager_proxy.achievedPointing[1:]
    assert achieved_az != pytest.approx(requested_az)
    assert achieved_el != pytest.approx(requested_el)

    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
@pytest.mark.forked
def test_abort_commands_during_stow(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
):
    """Test that AbortCommands aborts the executing stow command."""
    result_event_store = event_store_class()
    main_event_store = event_store_class()

    attr_cb_mapping = {
        "dishMode": main_event_store,
        "pointingState": main_event_store,
        "longRunningCommandResult": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    # Stow the dish
    dish_manager_proxy.SetStowMode()
    main_event_store.wait_for_value(PointingState.SLEW, timeout=10)

    # Call AbortCommands on DishManager
    [[_], [unique_id]] = dish_manager_proxy.AbortCommands()
    result_event_store.wait_for_command_result(
        unique_id, '[0, "Abort sequence completed"]', timeout=30
    )

    main_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=30)
    # Check that the dish is in standby FP mode
    assert dish_manager_proxy.dishMode == DishMode.STANDBY_FP
    # Check that the dish did not slew to the stow position
    stow_position = 90.2
    achieved_el = dish_manager_proxy.achievedPointing[2]
    assert achieved_el != pytest.approx(stow_position)

    remove_subscriptions(subscriptions)
