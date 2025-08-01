"""Fixtures for running ska-mid-dish-manager acceptance tests."""

import pytest

from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
)
from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.fixture(autouse=True)
def setup_and_teardown(event_store_class, dish_manager_proxy):
    """Reset the tango devices to a fresh state before each test."""
    dish_manager_proxy.Abort()
    event_store = event_store_class()
    dish_mode_events = event_store_class()

    subscriptions = {}
    subscriptions.update(
        setup_subscriptions(dish_manager_proxy, {"longRunningCommandsInQueue": event_store})
    )
    subscriptions.update(setup_subscriptions(dish_manager_proxy, {"dishMode": dish_mode_events}))

    try:
        event_store.wait_for_value((), timeout=30)
    except (RuntimeError, AssertionError):
        pass

    try:
        dish_mode_events.wait_for_value(DishMode.STANDBY_FP, timeout=10)
    except RuntimeError:
        # request FP mode and allow the test to continue
        dish_manager_proxy.SetStandbyFPMode()
        dish_mode_events.get_queue_values()
    finally:
        remove_subscriptions(subscriptions)

    yield
