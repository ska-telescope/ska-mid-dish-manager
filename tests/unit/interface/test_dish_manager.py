"""Unit tests checking DishManager behaviour."""
# pylint: disable=protected-access

import json
from datetime import datetime

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode, DSOperatingMode, SPFOperatingMode


@pytest.mark.unit
@pytest.mark.forked
def test_dish_manager_behaviour(dish_manager_resources, event_store_class):
    """Test that SetStandbyFPMode does 3 result updates. DishManager, DS, SPF"""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]

    result_event_store = event_store_class()
    progress_event_store = event_store_class()

    device_proxy.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )
    result_event_store.clear_queue()

    device_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    assert device_proxy.dishMode == DishMode.STANDBY_LP
    device_proxy.SetStandbyFPMode()
    progress_event_store.wait_for_progress_update("Awaiting dishMode change to STANDBY_FP")

    ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_FP)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)

    # Sample events:
    # ('longrunningcommandresult',
    # ('1659015778.0797186_172264627776495_DS_SetStandbyFPMode',
    #  '[0, "result"]'))

    # ('longrunningcommandresult',
    # ('1659015778.0823436_222123736715640_SPF_SetOperateMode',
    # '[0, "result"]'))

    # ('longrunningcommandresult',
    # ('1680213846.5427592_258218647656556_SetStandbyFPMode',
    # '[0, "SetStandbyFPMode completed"]'))

    events = result_event_store.wait_for_n_events(3, timeout=5)
    event_values = result_event_store.get_data_from_events(events)
    event_ids = [
        event_value[1][0] for event_value in event_values if event_value[1] and event_value[1][0]
    ]
    # Sort via command creation timestamp
    event_ids.sort(key=lambda x: datetime.fromtimestamp((float(x.split("_")[0]))))
    assert sorted([event_id.split("_")[-1] for event_id in event_ids]) == [
        "SetOperateMode",
        "SetStandbyFPMode",
        "SetStandbyFPMode",
    ]


@pytest.mark.unit
@pytest.mark.forked
def test_component_states(dish_manager_resources):
    """Test that GetComponentStates for 3 devices are returned"""
    device_proxy, _ = dish_manager_resources

    json_string = json.loads(device_proxy.GetComponentStates())
    assert "DS" in json_string
    assert "SPFRx" in json_string
    assert "SPF" in json_string


@pytest.mark.unit
@pytest.mark.forked
def test_connection_ping(dish_manager_resources):
    "Test that the monitoring command exists and is polled"
    device_proxy, _ = dish_manager_resources
    MONITOR_PING_POLL_PERIOD = 30000
    assert device_proxy.get_command_poll_period("MonitoringPing") == MONITOR_PING_POLL_PERIOD
