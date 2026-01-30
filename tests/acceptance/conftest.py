"""Fixtures for running ska-mid-dish-manager acceptance tests."""

import logging

import pytest

from ska_mid_dish_manager.models.constants import DEFAULT_ACTION_TIMEOUT_S
from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    DSPowerState,
    SPFOperatingMode,
    SPFRxOperatingMode,
)
from tests.utils import remove_subscriptions, setup_subscriptions

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


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
    event_store = event_store_class()
    dish_mode_events = event_store_class()
    result_events = event_store_class()
    # this wait is very important for our AUTOMATED tests!!!
    # wait for task status updates to finish before resetting the
    # sub devices to a clean state for the next test. Reasons are:
    # [*] your command map may never evaluate true for the
    # awaited value to report the final task status of the LRC.
    # [*] the base classes needs this final task status to allow the
    # subsequently issued commands to be moved from queued to in progress
    subs = setup_subscriptions(
        dish_manager_proxy, {"longRunningCommandsInQueue": event_store}, reset_queue=False
    )
    try:
        # it takes 10 seconds for the LRC marked as completed,
        # aborted, failed or rejected to be removed
        event_store.wait_for_value((), timeout=10)
    except RuntimeError:
        # carry on with the test even if the LRC is not cleared.
        # the executor will pick up the next queued command since
        # those commands from the previous test are not in progress.
        pass
    finally:
        remove_subscriptions(subs)

    subscriptions = {}
    subscriptions.update(setup_subscriptions(spf_device_proxy, {"operatingMode": event_store}))
    subscriptions.update(setup_subscriptions(spfrx_device_proxy, {"operatingMode": event_store}))
    subscriptions.update(setup_subscriptions(ds_device_proxy, {"operatingMode": event_store}))
    subscriptions.update(
        setup_subscriptions(
            dish_manager_proxy,
            {
                "dishMode": dish_mode_events,
                "longRunningCommandResult": result_events,
                "dscCmdAuth": event_store,
            },
        )
    )

    try:
        if dish_manager_proxy.dishMode == DishMode.MAINTENANCE:
            dish_manager_proxy.SetStowMode()
            dish_mode_events.wait_for_value(DishMode.STOW, timeout=10)

        if dish_manager_proxy.dishmode != DishMode.STANDBY_LP:
            spf_device_proxy.ResetToDefault()
            assert event_store.wait_for_value(SPFOperatingMode.STANDBY_LP, timeout=10)

            spfrx_device_proxy.ResetToDefault()
            assert event_store.wait_for_value(SPFRxOperatingMode.STANDBY, timeout=10)

            if (
                ds_device_proxy.operatingMode != DSOperatingMode.STANDBY
                or ds_device_proxy.powerstate != DSPowerState.LOW_POWER
            ):
                # go to LP ...
                ds_device_proxy.SetStandbyMode()
            dish_mode_events.wait_for_value(DishMode.STANDBY_LP, timeout=30)
    except (RuntimeError, AssertionError):
        # check dish manager before giving up
        logger.exception("Failed to reset subdevices to known states.")
        logger.info("DishManager commands: %s", dish_manager_proxy.longrunningcommandstatus)
        logger.info("DSManager commands: %s", dish_manager_proxy.longrunningcommandstatus)

    try:
        if dish_manager_proxy.dishmode != DishMode.STANDBY_FP:
            [[_], [unique_id]] = dish_manager_proxy.SetStandbyFPMode()
            result_events.wait_for_command_id(unique_id, timeout=30)
            dish_mode_events.wait_for_value(DishMode.STANDBY_FP, timeout=30)
    except RuntimeError:
        component_states = dish_manager_proxy.GetComponentStates()
        dish_mode = dish_manager_proxy.read_attribute("dishMode").value
        assert dish_mode == DishMode.STANDBY_FP, component_states
    finally:
        remove_subscriptions(subscriptions)

    yield
