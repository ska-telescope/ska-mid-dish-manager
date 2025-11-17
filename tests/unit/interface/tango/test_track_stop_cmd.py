"""Unit tests for the TrackStop command."""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    PointingState,
    SPFOperatingMode,
    SPFRxOperatingMode,
)


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "current_pointing_state",
    [
        PointingState.READY,
        PointingState.SCAN,
    ],
)
def test_track_stop_cmd_fails_in_wrong_pointing_state(
    dish_manager_resources,
    event_store_class,
    current_pointing_state,
):
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]

    pointing_state_event_store = event_store_class()
    lrc_status_event_store = event_store_class()

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

    ds_cm._update_component_state(pointingstate=current_pointing_state)
    pointing_state_event_store.wait_for_value(current_pointing_state, timeout=5)

    [[_], [unique_id]] = device_proxy.TrackStop()
    lrc_status_event_store.wait_for_value((unique_id, "REJECTED"))


@pytest.mark.unit
@pytest.mark.forked
def test_track_stop_cmd_succeeds_when_pointing_state_is_track(
    dish_manager_resources,
    event_store_class,
):
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]
    spfrx_cm = dish_manager_cm.sub_component_managers["SPFRX"]

    main_event_store = event_store_class()
    status_event_store = event_store_class()

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
        "Status",
        tango.EventType.CHANGE_EVENT,
        status_event_store,
    )

    # Force dishManager dishMode to go to OPERATE
    ds_cm._update_component_state(operatingmode=DSOperatingMode.POINT)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.OPERATE)
    main_event_store.wait_for_value(DishMode.OPERATE)
    ds_cm._update_component_state(pointingstate=PointingState.READY)
    main_event_store.wait_for_value(PointingState.READY)

    # Clear out the queue to make sure we don't catch old events
    main_event_store.clear_queue()

    # Request Track on Dish
    [[_], [unique_id]] = device_proxy.Track()
    main_event_store.wait_for_command_id(unique_id, timeout=6)
    # wait a bit before forcing the updates on the subcomponents
    main_event_store.get_queue_values()

    # Transition of DS pointingState to TRACK
    ds_cm._update_component_state(pointingstate=PointingState.SLEW)
    main_event_store.wait_for_value(PointingState.SLEW)

    ds_cm._update_component_state(pointingstate=PointingState.TRACK)
    main_event_store.wait_for_value(PointingState.TRACK)

    # Request TrackStop on Dish
    device_proxy.TrackStop()
    # wait a bit before forcing the updates on the subcomponents
    main_event_store.get_queue_values()

    # transition DS pointingState to READY
    ds_cm._update_component_state(pointingstate=PointingState.READY)
    main_event_store.wait_for_value(PointingState.READY)

    expected_progress_updates = [
        "Fanned out commands: DS.TrackStop",
        "Awaiting DS pointingstate change to READY",
        "TrackStop completed",
    ]

    events = status_event_store.wait_for_progress_update(expected_progress_updates[-1], timeout=6)

    events_string = "".join([str(event.attr_value.value) for event in events])
    for message in expected_progress_updates:
        assert message in events_string
