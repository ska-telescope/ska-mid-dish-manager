"""Unit tests for the ConfigureBand2 command on dish manager."""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
    DSOperatingMode,
    DSPowerState,
    IndexerPosition,
    SPFBandInFocus,
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
    status_event_store = event_store_class()

    for attr in [
        "dishMode",
        "lrcFinished",
        "configuredBand",
    ]:
        device_proxy.subscribe_event(
            attr,
            tango.EventType.CHANGE_EVENT,
            main_event_store,
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
    status_event_store.wait_for_progress_update(
        "Awaiting dishmode change to STANDBY_FP", timeout=120
    )

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

    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.CONFIGURE)
    spfrx_cm._update_component_state(operatingmode=SPFRxOperatingMode.OPERATE)
    spfrx_cm._update_component_state(configuredband=Band[band_number])
    ds_cm._update_component_state(
        indexerposition=IndexerPosition[band_number], operatingmode=DSOperatingMode.POINT
    )
    spf_cm._update_component_state(bandinfocus=SPFBandInFocus[band_number])

    assert main_event_store.wait_for_command_id(unique_id, timeout=40)
    assert device_proxy.configuredBand == Band[band_number]

    expected_progress_updates = [
        "DS operatingmode changed to STANDBY",
        "DS.SetStandbyMode completed",
        "DS powerstate changed to FULL_POWER",
        "DS.SetPowerMode completed",
        "SPF operatingmode changed to OPERATE",
        "SPF.SetOperateMode completed",
        "SetStandbyFPMode completed.",
        f"{command} started",
        "DS.SetIndexPosition started",
        f"Awaiting DS indexerposition change to {band_number}",
        "Running SetIndexPosition on device DS",
        "Not waiting on SetIndexPosition on DS as the timeout is 0",
        f"SPFRX.{command} started",
        f"Running {command} on device SPFRX",
        f"Not waiting on {command} on SPFRX as the timeout is 0",
        "Awaiting SPFRX operatingmode change to CONFIGURE",
        "Running Wait for operatingMode.CONFIGURE on device SPFRX",
        "Awaiting SPFRX operatingmode change to CONFIGURE",
        "SPFRX operatingmode changed to CONFIGURE",
        "SPFRX.Wait for operatingMode.CONFIGURE completed",
        f"{command}: Wait for operatingMode.CONFIGURE on device SPFRX completed",
        "Awaiting SPFRX operatingmode change to OPERATE",
        "Running Wait for operatingMode.OPERATE on device SPFRX",
        "Awaiting SPFRX operatingmode change to OPERATE",
        "SPFRX operatingmode changed to OPERATE",
        "SPFRX.Wait for operatingMode.OPERATE completed",
        f"{command}: Wait for operatingMode.OPERATE on device SPFRX completed",
        f"Awaiting SPFRX configuredband change to {band_number}",
        f"Running Wait for configuredband {band_number.replace('B', '')} on device SPFRX",
        f"Awaiting SPFRX configuredband change to {band_number}",
        f"SPFRX configuredband changed to {band_number}",
        f"SPFRX.Wait for configuredband {band_number.replace('B', '')} completed",
        (
            f"{command}: Wait for configuredband {band_number.replace('B', '')} on"
            " device SPFRX completed"
        ),
        f"{command} complete. Triggering on success action.",
    ]

    events = status_event_store.wait_for_progress_update(expected_progress_updates[-1], timeout=40)

    for i in [str(event.attr_value.value) for event in events]:
        print("AAAAA", i)

    events_string = "".join([str(event.attr_value.value) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string
