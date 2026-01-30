"""Fixtures for running ska-mid-dish-manager acceptance tests."""

import logging

import pytest
import tango

from ska_mid_dish_manager.models.constants import (
    DEFAULT_ACTION_TIMEOUT_S,
    DEFAULT_DISH_MANAGER_TRL,
)
from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    DSPowerState,
)
from tests.utils import EventStore, remove_subscriptions, setup_subscriptions

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def pytest_sessionstart(session: pytest.Session) -> None:
    """Ensure dish manager is ready at the start of the tests."""
    event_store = EventStore()
    dish_manager = tango.DeviceProxy(DEFAULT_DISH_MANAGER_TRL)
    dish_manager.subscribe_event("State", tango.EventType.CHANGE_EVENT, event_store)
    try:
        event_store.wait_for_value(tango.DevState.ON, timeout=120)
    except RuntimeError as e:
        # continue with tests but log the issue in case tests fail later
        print(f"Dish manager not ready for tests: {e}")


@pytest.fixture
def undo_raise_exceptions(spf_device_proxy, spfrx_device_proxy):
    """Undo any updates to raiseCmdException in SPF and SPFRx."""
    yield
    spf_device_proxy.raiseCmdException = False
    spfrx_device_proxy.raiseCmdException = False


@pytest.fixture
def toggle_skip_attributes(spf_device_proxy):
    """Ensure that attribute updates on spf is restored."""
    # Set a flag on SPF to skip attribute updates.
    # This is useful to ensure that the long running command
    # does not finish executing
    spf_device_proxy.skipAttributeUpdates = True
    yield
    spf_device_proxy.skipAttributeUpdates = False


@pytest.fixture
def restore_action_timeout(dish_manager_proxy):
    """Ensure that attribute updates on spf is restored."""
    yield
    dish_manager_proxy.actionTimeoutSeconds = DEFAULT_ACTION_TIMEOUT_S


@pytest.fixture
def reset_dish_to_standby(
    event_store_class,
    dish_manager_proxy,
    ds_device_proxy,
    spf_device_proxy,
    spfrx_device_proxy,
):
    """Reset the tango devices to a fresh state before each test."""
    op_mode_events = event_store_class()
    power_state_events = event_store_class()
    dish_mode_events = event_store_class()

    lrc_status = dish_manager_proxy.longRunningCommandStatus
    lrc_status = ", ".join([evt for evt in lrc_status])
    if "IN_PROGRESS" in lrc_status:
        # this wait is very important for our AUTOMATED tests!!!
        # wait for task status updates to finish before resetting the
        # sub devices to a clean state for the next test. Reasons are:
        # [*] your command map may never evaluate true for the
        # awaited value to report the final task status of the LRC.
        # [*] the base classes needs this final task status to allow the
        # subsequently issued commands to be moved from queued to in progress
        op_mode_events.get_queue_events(timeout=5)

    subscriptions = {}
    subscriptions.update(
        setup_subscriptions(
            ds_device_proxy,
            {"operatingMode": op_mode_events, "powerState": power_state_events},
        )
    )
    subscriptions.update(setup_subscriptions(dish_manager_proxy, {"dishMode": dish_mode_events}))

    # reset the simulated devices
    spfrx_device_proxy.ResetToDefault()
    spf_device_proxy.ResetToDefault()

    try:
        if dish_manager_proxy.dishMode == DishMode.MAINTENANCE:
            dish_manager_proxy.SetStowMode()
            dish_mode_events.wait_for_value(DishMode.STOW, timeout=120)

        if ds_device_proxy.operatingMode != DSOperatingMode.STANDBY:
            ds_device_proxy.SetStandbyMode()
            op_mode_events.wait_for_value(DSOperatingMode.STANDBY, timeout=10)
            power_state_events.wait_for_value(DSPowerState.LOW_POWER, timeout=10)
        # go to FP
        ds_device_proxy.SetPowerMode([0.0, 14.7])
        power_state_events.wait_for_value(DSPowerState.FULL_POWER, timeout=10)

    except (RuntimeError, AssertionError):
        pass

    if dish_manager_proxy.dishMode != DishMode.STANDBY_FP:
        dish_manager_proxy.SetStandbyFPMode()
        try:
            dish_mode_events.wait_for_value(DishMode.STANDBY_FP, timeout=10)
        except RuntimeError:
            logger.debug("DishManager commands: %s", dish_manager_proxy.longrunningcommandstatus)
            logger.debug("DSManager commands: %s", ds_device_proxy.longrunningcommandstatus)
            logger.debug("\n\nDM component state: %s\n\n", dish_manager_proxy.GetComponentStates())
            remove_subscriptions(subscriptions)
            raise

    remove_subscriptions(subscriptions)

    yield
