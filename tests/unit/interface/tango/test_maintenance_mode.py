"""Unit tests verify SetMaintenanceMode behaviour."""

from unittest.mock import call

import pytest
import tango
from ska_control_model import TaskStatus

from ska_mid_dish_manager.models.dish_enums import DishMode, DSOperatingMode, SPFOperatingMode
from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.mark.unit
@pytest.mark.forked
def test_happy_case(dish_manager_resources, event_store_class):
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]

    dish_mode_event_store = event_store_class()
    status_event_store = event_store_class()
    result_event_store = event_store_class()

    attr_cb_mapping = {
        "lrcFinished": result_event_store,
        "dishMode": dish_mode_event_store,
    }

    device_proxy.subscribe_event(
        "Status",
        tango.EventType.CHANGE_EVENT,
        status_event_store,
    )
    subscriptions = setup_subscriptions(device_proxy, attr_cb_mapping)

    device_proxy.SetMaintenanceMode()
    result_event_store.get_queue_values()
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STOW)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.MAINTENANCE)

    expected_progress_update = "SetMaintenanceMode completed"
    status_event_store.wait_for_progress_update(expected_progress_update, timeout=60)
    dish_mode_event_store.wait_for_value(DishMode.MAINTENANCE)

    # Check that the ReleaseAuth command was executed
    execute_command_args = ds_cm.execute_command.call_args_list[-1]
    assert execute_command_args == call("ReleaseAuth", None)

    remove_subscriptions(subscriptions)


@pytest.mark.unit
@pytest.mark.forked
def test_dish_does_not_stow(dish_manager_resources, event_store_class):
    device_proxy, _ = dish_manager_resources
    result_event_store = event_store_class()

    subscriptions = setup_subscriptions(device_proxy, {"lrcFinished": result_event_store})

    init_dish_mode = device_proxy.dishMode

    device_proxy.SetMaintenanceMode()
    result_event_store.get_queue_values()

    assert device_proxy.dishMode == init_dish_mode

    remove_subscriptions(subscriptions)


@pytest.mark.unit
@pytest.mark.forked
def test_exception_on_callback(dish_manager_resources, event_store_class):
    """Test that SetMaintenanceMode handles exceptions properly when subdevice command fails."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]

    result_event_store = event_store_class()

    attr_cb_mapping = {
        "lrcFinished": result_event_store,
    }
    subscriptions = setup_subscriptions(device_proxy, attr_cb_mapping)

    ds_cm.execute_command.return_value = TaskStatus.FAILED, "Simulated failure"

    [[_], [unique_id]] = device_proxy.SetMaintenanceMode()

    expected_result = '[3, "SetMaintenanceMode failed"]'

    result_event_store.wait_for_finished_command_result(unique_id, expected_result, timeout=10)

    remove_subscriptions(subscriptions)
