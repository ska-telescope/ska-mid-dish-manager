"""Test AbortCommands."""

import pytest

from ska_mid_dish_manager.models.dish_enums import DishMode
from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.fixture
def toggle_skip_attributes(event_store_class, spf_device_proxy, dish_manager_proxy):
    """Ensure that attribute updates on spf is restored."""
    dish_manager_proxy.SetStandbyLPMode()
    dish_mode_event_store = event_store_class()
    sub = setup_subscriptions(dish_manager_proxy, {"dishMode": dish_mode_event_store})
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_LP, timeout=10)
    remove_subscriptions(sub)
    # Set a flag on SPF to skip attribute updates.
    # This is useful to ensure that the long running command
    # does not finish executing before AbortCommands is triggered
    spf_device_proxy.skipAttributeUpdates = True
    yield
    spf_device_proxy.skipAttributeUpdates = False


@pytest.mark.acceptance
@pytest.mark.forked
def test_abort_commands(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
    toggle_skip_attributes,
):
    """Test AbortCommands aborts the executing long running command."""
    dish_mode_event_store = event_store_class()
    progress_event_store = event_store_class()
    cmds_in_queue_store = event_store_class()

    attr_cb_mapping = {
        "dishMode": dish_mode_event_store,
        "longRunningCommandProgress": progress_event_store,
        "longRunningCommandsInQueue": cmds_in_queue_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    # Transition to FP mode
    dish_manager_proxy.SetStandbyFPMode()

    # Check that Dish Manager is waiting to transition to FP
    progress_event_store.wait_for_progress_update(
        "Awaiting dishmode change to STANDBY_FP", timeout=30
    )
    # Check that the Dish Manager did not transition to FP
    dish_mode_event_store.wait_for_value(DishMode.UNKNOWN)
    assert dish_manager_proxy.dishMode == DishMode.UNKNOWN

    # Abort the LRC
    dish_manager_proxy.AbortCommands()
    # Confirm Dish Manager aborted the request on LRC
    progress_event_store.wait_for_progress_update("SetStandbyFPMode Aborted", timeout=30)
    # Confirm that abort finished and the queue is cleared
    cmds_in_queue_store.wait_for_value((), timeout=30)

    remove_subscriptions(subscriptions)
