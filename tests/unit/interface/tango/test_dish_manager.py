"""Unit tests checking DishManager behaviour."""

import json

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode, DSOperatingMode, SPFOperatingMode


@pytest.mark.unit
@pytest.mark.forked
def test_dish_manager_behaviour(dish_manager_resources, event_store_class):
    """Test that SetStandbyFPMode result updates."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]

    result_event_store = event_store_class()
    status_event_store = event_store_class()

    device_proxy.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )
    result_event_store.clear_queue()

    device_proxy.subscribe_event(
        "Status",
        tango.EventType.CHANGE_EVENT,
        status_event_store,
    )

    assert device_proxy.dishMode == DishMode.STANDBY_LP
    device_proxy.SetStandbyFPMode()
    status_event_store.wait_for_progress_update("Awaiting dishmode change to STANDBY_FP")

    ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_FP)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)

    events = result_event_store.wait_for_n_events(1, timeout=5)
    event_values = result_event_store.get_data_from_events(events)
    event_value = event_values[0][1]
    # Sample event value:
    # ('1659015778.0797186_172264627776495_DS_SetStandbyFPMode', '[0, "result"]'))
    command_name = event_value[0].split("_")[-1]
    assert command_name == "SetStandbyFPMode"


@pytest.mark.unit
@pytest.mark.forked
def test_component_states(dish_manager_resources):
    """Test that GetComponentStates for 3 devices are returned."""
    device_proxy, _ = dish_manager_resources

    json_string = json.loads(device_proxy.GetComponentStates())
    assert "DS" in json_string
    assert "SPFRx" in json_string
    assert "SPF" in json_string
