"""Test command timeout."""

import time

import pytest

from ska_mid_dish_manager.models.constants import DEFAULT_ACTION_TIMEOUT_S
from ska_mid_dish_manager.models.dish_enums import DishMode
from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.mark.acceptance
def test_action_timeout(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
    ds_device_proxy,
    toggle_skip_attributes,
    restore_action_timeout,
):
    """Test commanded action timeout."""
    dish_mode_event_store = event_store_class()
    status_event_store = event_store_class()
    result_event_store = event_store_class()
    cmds_in_queue_store = event_store_class()

    attr_cb_mapping = {
        "dishMode": dish_mode_event_store,
        "longRunningCommandResult": result_event_store,
        "longRunningCommandsInQueue": cmds_in_queue_store,
        "Status": status_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    try:
        dish_manager_proxy.actionTimeoutSeconds = 3

        # Attempt to configure which will take SPF to Operate mode, this won't happen as
        # skipAttributeUpdates was set to True
        [[_], [configure_unique_id]] = dish_manager_proxy.ConfigureBand1(True)

        # Check that Dish Manager is waiting to transition
        status_event_store.wait_for_progress_update("Awaiting configuredband change to B1")
        # Check that the Dish Manager did not transition
        dish_mode_event_store.wait_for_value(DishMode.UNKNOWN, timeout=10)
        assert dish_manager_proxy.dishMode == DishMode.UNKNOWN

        result_event_store.wait_for_command_result(
            configure_unique_id, '[3, "SetOperateMode failed"]', timeout=5
        )

        dish_manager_proxy.actionTimeoutSeconds = DEFAULT_ACTION_TIMEOUT_S

        # Bring the dish back to a known state
        ds_device_proxy.SetStandbyMode()
        dish_mode_event_store.wait_for_value(DishMode.STANDBY_LP, timeout=10)

        [[_], [configure_unique_id]] = dish_manager_proxy.ConfigureBand2(True)

        # Check that Dish Manager is waiting to transition
        status_event_store.wait_for_progress_update("Awaiting configuredband change to B2")

        time.sleep(DEFAULT_ACTION_TIMEOUT_S // 2)

        # Check that the LRC status still reports IN_PROGRESS
        lrc_statuses: list[str] = dish_manager_proxy.longrunningcommandstatus

        assert configure_unique_id in lrc_statuses
        id_index = lrc_statuses.index(configure_unique_id)
        status_index = id_index + 1
        assert lrc_statuses[status_index] == "IN_PROGRESS"

        # Wait for time out
        result_event_store.wait_for_command_result(
            configure_unique_id, '[3, "SetOperateMode failed"]', timeout=DEFAULT_ACTION_TIMEOUT_S
        )
    except RuntimeError:
        # Call Abort on DishManager if anything goes wrong so the LRCs aren't stuck
        # IN_PROGRESS
        [[_], [unique_id]] = dish_manager_proxy.Abort()
        result_event_store.wait_for_command_result(
            unique_id, '[0, "Abort sequence completed"]', timeout=30
        )
        dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=30)
    finally:
        remove_subscriptions(subscriptions)
