"""Unit tests for the Slew command."""

import pytest
import tango
from ska_mid_dish_utils.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    DSPowerState,
    PointingState,
    SPFOperatingMode,
    SPFRxOperatingMode,
)


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
def test_set_slew_cmd_fails_when_dish_mode_is_not_operate(
    dish_manager_resources,
    event_store_class,
    current_dish_mode,
):
    device_proxy, dish_manager_cm = dish_manager_resources
    dish_mode_event_store = event_store_class()
    pointing_state_event_store = event_store_class()
    lrc_status_event_store = event_store_class()
    status_event_store = event_store_class()

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

    device_proxy.subscribe_event(
        "Status",
        tango.EventType.CHANGE_EVENT,
        status_event_store,
    )

    dish_manager_cm._update_component_state(pointingstate=PointingState.READY)
    pointing_state_event_store.wait_for_value(PointingState.READY, timeout=5)

    dish_manager_cm._update_component_state(dishmode=current_dish_mode)
    dish_mode_event_store.wait_for_value(current_dish_mode, timeout=5)

    [[_], [unique_id]] = device_proxy.Slew([0.0, 50.0])
    lrc_status_event_store.wait_for_value((unique_id, "REJECTED"))

    expected_progress_updates = (
        "Slew command rejected for current dishMode. Slew command is allowed for dishMode OPERATE"
    )
    status_event_store.wait_for_progress_update(expected_progress_updates, timeout=6)


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "current_pointing_state",
    [
        PointingState.SLEW,
        PointingState.TRACK,
        PointingState.SCAN,
        PointingState.UNKNOWN,
    ],
)
def test_set_slew_cmd_fails_when_pointing_state_is_not_ready(
    dish_manager_resources,
    event_store_class,
    current_pointing_state,
):
    device_proxy, dish_manager_cm = dish_manager_resources
    dish_mode_event_store = event_store_class()
    pointing_state_event_store = event_store_class()
    lrc_status_event_store = event_store_class()
    status_event_store = event_store_class()

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

    device_proxy.subscribe_event(
        "Status",
        tango.EventType.CHANGE_EVENT,
        status_event_store,
    )

    dish_manager_cm._update_component_state(dishmode=DishMode.OPERATE)
    dish_mode_event_store.wait_for_value(DishMode.OPERATE, timeout=5)

    dish_manager_cm._update_component_state(pointingstate=current_pointing_state)
    pointing_state_event_store.wait_for_value(current_pointing_state, timeout=5)

    [[_], [unique_id]] = device_proxy.Slew([0.0, 50.0])
    lrc_status_event_store.wait_for_value((unique_id, "REJECTED"))

    expected_progress_updates = (
        "Slew command rejected for current pointingState. "
        "Slew command is allowed for pointingState READY"
    )
    status_event_store.wait_for_progress_update(expected_progress_updates, timeout=6)


@pytest.mark.unit
@pytest.mark.forked
def test_set_slew_cmd_succeeds_when_dish_mode_is_operate(
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

    ds_cm._update_component_state(
        operatingmode=DSOperatingMode.POINT,
        powerstate=DSPowerState.FULL_POWER,
    )
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.OPERATE)
    main_event_store.wait_for_value(DishMode.OPERATE)
    ds_cm._update_component_state(pointingstate=PointingState.READY)
    main_event_store.wait_for_value(PointingState.READY)

    # Clear out the queue to make sure we don't catch old events
    main_event_store.clear_queue()

    # Request Slew on Dish
    device_proxy.Slew([0.0, 50.0])
    # wait a bit before forcing the updates on the subcomponents
    main_event_store.get_queue_values()

    # Transition DS pointingState to Slew
    ds_cm._update_component_state(pointingstate=PointingState.SLEW)
    main_event_store.wait_for_value(PointingState.SLEW)

    expected_progress_updates = [
        "Fanned out commands: DS.Slew",
        "The DS has been commanded to Slew to [ 0. 50.]. "
        "Monitor the pointing attributes for the completion status of the task.",
    ]

    events = status_event_store.wait_for_progress_update(expected_progress_updates[-1], timeout=6)

    events_string = "".join([str(event.attr_value.value) for event in events])

    # Check that all the expected progress messages appeared
    for message in expected_progress_updates:
        assert message in events_string


@pytest.mark.unit
@pytest.mark.forked
def test_set_slew_cmd_rejected_invalid_inputs(
    dish_manager_resources,
    event_store_class,
):
    device_proxy, dish_manager_cm = dish_manager_resources
    lrc_status_event_store = event_store_class()

    device_proxy.subscribe_event(
        "longRunningCommandStatus",
        tango.EventType.CHANGE_EVENT,
        lrc_status_event_store,
    )

    # Clear out the queue to make sure we don't catch old events
    lrc_status_event_store.clear_queue()

    device_proxy.Slew([0.0, 50.0, 100.0])
    event_queue = lrc_status_event_store.get_queue_values()
    # Produces a data structure looking like
    # [('longrunningcommandstatus', ('1768312843.152686_270411648951242_Slew', 'STAGING')),
    # ('longrunningcommandstatus', ('1768312843.152686_270411648951242_Slew', 'REJECTED'))],
    # so we index to find the correct value
    expected_status = event_queue[1][1][1]
    assert expected_status == "REJECTED"
