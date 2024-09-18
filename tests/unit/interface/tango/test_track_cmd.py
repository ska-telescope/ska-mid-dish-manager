"""Unit tests for the Track command."""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    PointingState,
    SPFOperatingMode,
    SPFRxOperatingMode,
    TrackInterpolationMode,
)


# pylint: disable=missing-function-docstring, protected-access
@pytest.mark.unit
@pytest.mark.forked
def test_track_interpolation_mode_updates(dish_manager_resources, event_store_class):
    """Test the trackInterpolationMode attribute updates on change."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]

    event_store = event_store_class()
    device_proxy.subscribe_event(
        "trackInterpolationMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    test_mode = TrackInterpolationMode.NEWTON

    # Check that the default is spline
    assert device_proxy.trackInterpolationMode == TrackInterpolationMode.SPLINE

    # Check that the value updates correctly
    ds_cm._update_component_state(trackinterpolationmode=test_mode)

    event_store.wait_for_value(test_mode)
    assert device_proxy.trackInterpolationMode == test_mode


# pylint: disable=missing-function-docstring, protected-access
@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "current_dish_mode",
    [
        DishMode.STANDBY_LP,
        DishMode.STANDBY_FP,
        DishMode.STARTUP,
        DishMode.SHUTDOWN,
        DishMode.MAINTENANCE,
        DishMode.STOW,
        DishMode.CONFIG,
    ],
)
def test_set_track_cmd_fails_when_dish_mode_is_not_operate(
    dish_manager_resources,
    event_store_class,
    current_dish_mode,
):
    device_proxy, dish_manager_cm = dish_manager_resources
    dish_mode_event_store = event_store_class()
    pointing_state_event_store = event_store_class()
    lrc_status_event_store = event_store_class()

    device_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )

    device_proxy.subscribe_event(
        "pointingState",
        tango.EventType.CHANGE_EVENT,
        pointing_state_event_store,
    )

    device_proxy.subscribe_event(
        "longRunningCommandStatus",
        tango.EventType.CHANGE_EVENT,
        lrc_status_event_store,
    )

    # Ensure that the pointingState precondition is met before testing Track() against dishMode
    dish_manager_cm._update_component_state(pointingstate=PointingState.READY)
    pointing_state_event_store.wait_for_value(PointingState.READY, timeout=5)

    dish_manager_cm._update_component_state(dishmode=current_dish_mode)
    dish_mode_event_store.wait_for_value(current_dish_mode, timeout=5)

    [[_], [unique_id]] = device_proxy.Track()
    lrc_status_event_store.wait_for_value((unique_id, "REJECTED"))


# pylint: disable=missing-function-docstring, protected-access
@pytest.mark.unit
@pytest.mark.forked
def test_set_track_cmd_succeeds_when_dish_mode_is_operate(
    dish_manager_resources,
    event_store_class,
):
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]
    spfrx_cm = dish_manager_cm.sub_component_managers["SPFRX"]

    main_event_store = event_store_class()
    progress_event_store = event_store_class()

    attributes_to_subscribe_to = (
        "dishMode",
        "longRunningCommandResult",
        "pointingState",
    )
    for attribute_name in attributes_to_subscribe_to:
        device_proxy.subscribe_event(
            attribute_name,
            tango.EventType.CHANGE_EVENT,
            main_event_store,
        )

    device_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    # Force dishManager dishMode to go to OPERATE
    ds_cm._update_component_state(operatingmode=DSOperatingMode.POINT)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.DATA_CAPTURE)
    main_event_store.wait_for_value(DishMode.OPERATE)
    ds_cm._update_component_state(pointingstate=PointingState.READY)
    main_event_store.wait_for_value(PointingState.READY)

    # Clear out the queue to make sure we don't catch old events
    main_event_store.clear_queue()

    # Request Track on Dish
    device_proxy.Track()
    # wait a bit before forcing the updates on the subcomponents
    main_event_store.get_queue_values()

    # Transition DS pointingState to TRACK
    ds_cm._update_component_state(pointingstate=PointingState.SLEW)
    main_event_store.wait_for_value(PointingState.SLEW)

    ds_cm._update_component_state(pointingstate=PointingState.TRACK)
    main_event_store.wait_for_value(PointingState.TRACK)

    expected_progress_updates = [
        "Track called on DS, ID",
        "Track command has been executed on DS. "
        "Monitor the achievedTargetLock attribute to determine when the dish is on source.",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string
