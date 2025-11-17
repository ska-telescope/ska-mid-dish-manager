"""Unit tests for the ConfigureBand2 command on dish manager."""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    BandInFocus,
    DishMode,
    DSOperatingMode,
    DSPowerState,
    IndexerPosition,
    SPFOperatingMode,
    SPFRxOperatingMode,
)


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "command,band_number",
    [
        ("ConfigureBand1", "B1"),
        ("ConfigureBand2", "B2"),
    ],
)
def test_configure_band_cmd_succeeds_when_dish_mode_is_standbyfp(
    command, band_number, dish_manager_resources, event_store_class
):
    """Test ConfigureBand."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]
    spfrx_cm = dish_manager_cm.sub_component_managers["SPFRX"]

    main_event_store = event_store_class()
    progress_event_store = event_store_class()
    status_event_store = event_store_class()

    for attr in [
        "dishMode",
        "longRunningCommandResult",
        "configuredBand",
    ]:
        device_proxy.subscribe_event(
            attr,
            tango.EventType.CHANGE_EVENT,
            main_event_store,
        )

    device_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )
    device_proxy.subscribe_event(
        "Status",
        tango.EventType.CHANGE_EVENT,
        status_event_store,
    )

    assert device_proxy.dishMode == DishMode.STANDBY_LP

    # Clear out the queue to make sure we don't catch old events
    main_event_store.clear_queue()

    [[_], [unique_id]] = device_proxy.SetStandbyFPMode()
    status_event_store.wait_for_progress_update("Awaiting dishmode change to STANDBY_FP")

    ds_cm._update_component_state(
        operatingmode=DSOperatingMode.STANDBY, powerstate=DSPowerState.FULL_POWER
    )
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.STANDBY)

    assert main_event_store.wait_for_command_id(unique_id, timeout=6)
    assert device_proxy.dishMode == DishMode.STANDBY_FP

    [[_], [unique_id]] = device_proxy.command_inout(command, True)
    # wait a bit before forcing the updates on the subcomponents
    main_event_store.get_queue_values()

    spfrx_cm._update_component_state(
        configuredband=Band[band_number], operatingmode=SPFRxOperatingMode.OPERATE
    )
    ds_cm._update_component_state(
        indexerposition=IndexerPosition[band_number], operatingmode=DSOperatingMode.POINT
    )
    spf_cm._update_component_state(bandinfocus=BandInFocus[band_number])

    assert main_event_store.wait_for_command_id(unique_id, timeout=5)
    assert device_proxy.configuredBand == Band[band_number]

    expected_progress_updates = [
        f"Fanned out commands: DS.SetIndexPosition, SPFRX.{command}",
        f"Awaiting configuredband change to {band_number}",
        f"{command} completed",
    ]

    events = status_event_store.wait_for_progress_update(expected_progress_updates[-1], timeout=6)

    events_string = "".join([str(event.attr_value.value) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string
