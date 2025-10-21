"""Test command timeout."""

import pytest

from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
)
from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.mark.acceptance
@pytest.mark.forked
@pytest.mark.skip
def test_action_timeout(
    reset_dish_to_standby,
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

    dish_manager_proxy.actionTimeoutSeconds = 3

    # Attempt to configure which will take SPF to Operate mode, this won't happen as
    # skipAttributeUpdates was set to True
    [[_], [configure_unique_id]] = dish_manager_proxy.ConfigureBand1(True)

    # Check that Dish Manager is waiting to transition
    progress_event_store.wait_for_progress_update("Awaiting configuredband change to B1")
    # Check that the Dish Manager did not transition
    dish_mode_event_store.wait_for_value(DishMode.UNKNOWN, timeout=10)
    assert dish_manager_proxy.dishMode == DishMode.UNKNOWN

    ret = result_event_store.result_event_store.wait_for_command_result(
        configure_unique_id, '[3, "SetOperateMode failed"]', timeout=30
    )

    dish_manager_proxy.actionTimeoutSeconds = 60

    [[_], [configure_unique_id]] = dish_manager_proxy.ConfigureBand2(True)

    # TODO: Wait N seconds (< 60) and check that command is still running, then finish the operate
    # changes and wait for the command to complete

    print(ret)
    assert 0

    remove_subscriptions(subscriptions)
