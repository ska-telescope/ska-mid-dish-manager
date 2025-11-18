"""Unit tests for setoperatemode command."""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    BandInFocus,
    DishMode,
    DSOperatingMode,
    IndexerPosition,
    SPFOperatingMode,
    SPFRxOperatingMode,
)


@pytest.mark.unit
@pytest.mark.forked
def test_set_operate_mode_fails_when_already_in_operate_dish_mode(
    dish_manager_resources,
    event_store_class,
):
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]
    spfrx_cm = dish_manager_cm.sub_component_managers["SPFRX"]

    dish_mode_event_store = event_store_class()
    lrc_status_event_store = event_store_class()

    device_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )

    device_proxy.subscribe_event(
        "longRunningCommandStatus",
        tango.EventType.CHANGE_EVENT,
        lrc_status_event_store,
    )

    # Force dishManager dishMode to go to OPERATE
    ds_cm._update_component_state(operatingmode=DSOperatingMode.POINT)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.OPERATE)
    dish_mode_event_store.wait_for_value(DishMode.OPERATE)

    [[_], [unique_id]] = device_proxy.SetOperateMode()
    lrc_status_event_store.wait_for_value((unique_id, "REJECTED"))


@pytest.mark.unit
@pytest.mark.forked
def test_set_operate_mode_succeeds_from_standbyfp_dish_mode(
    dish_manager_resources,
    event_store_class,
):
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]
    spfrx_cm = dish_manager_cm.sub_component_managers["SPFRX"]

    main_event_store = event_store_class()
    status_event_store = event_store_class()
    result_event_store = event_store_class()

    for attr in [
        "dishMode",
        "pointingState",
        "configuredBand",
    ]:
        device_proxy.subscribe_event(
            attr,
            tango.EventType.CHANGE_EVENT,
            main_event_store,
        )

    device_proxy.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )

    device_proxy.subscribe_event(
        "Status",
        tango.EventType.CHANGE_EVENT,
        status_event_store,
    )

    # Force dishManager dishMode to go to STANDBY_FP
    device_proxy.SetStandbyFPMode()
    status_event_store.wait_for_progress_update("Awaiting dishmode change to STANDBY_FP")
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_FP)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    main_event_store.wait_for_value(DishMode.STANDBY_FP)

    # Transition DishManager to OPERATE mode with configuredBand not set
    [[_], [unique_id]] = device_proxy.SetOperateMode()
    result_event_store.wait_for_command_result(
        unique_id, '[6, "SetOperateMode requires a configured band"]'
    )

    # Set configuredBand and try again
    ds_cm._update_component_state(indexerposition=IndexerPosition.B1)
    spf_cm._update_component_state(bandinfocus=BandInFocus.B1)
    spfrx_cm._update_component_state(configuredband=Band.B1)
    # spfrx operating mode transitions to OPERATE after successful band configuration
    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.OPERATE)
    main_event_store.wait_for_value(Band.B1)

    device_proxy.SetOperateMode()
    # wait a bit for the lrc updates to come through
    main_event_store.get_queue_values()
    # transition subservient devices to their respective operatingMode
    # and observe that DishManager transitions dishMode to OPERATE mode
    # SPF are already in the expected operatingMode
    ds_cm._update_component_state(operatingmode=DSOperatingMode.POINT)
    main_event_store.wait_for_value(DishMode.OPERATE)

    expected_progress_updates = [
        "Fanned out commands: SPF.SetOperateMode, DS.SetPointMode",
        "Awaiting dishmode change to OPERATE",
        "SetOperateMode completed",
    ]
    events = status_event_store.wait_for_progress_update(expected_progress_updates[-1])
    events_string = "".join([str(event.attr_value.value) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string
