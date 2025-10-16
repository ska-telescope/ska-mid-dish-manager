"""Fixtures for running ska-mid-dish-manager acceptance tests."""

import logging

import pytest

from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DscCmdAuthType,
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
            # Unstow is a long running command on the DSManager so we don't need to increase our
            # proxy timeout for the alarm horn. Stow will block the proxy if used.
            ds_device_proxy.unstow()
            event_store.wait_for_value(DscCmdAuthType.LMC, timeout=20)
            event_store.wait_for_value(DSOperatingMode.STANDBY, timeout=20)
            dish_mode_events.clear_queue()
            dish_manager_proxy.SetStowMode()
            dish_mode_events.wait_for_value(DishMode.STOW, timeout=10)

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
            assert event_store.wait_for_value(DSOperatingMode.STANDBY, timeout=10)
        dish_mode_events.wait_for_value(DishMode.STANDBY_LP, timeout=10)
    except (RuntimeError, AssertionError):
        # check dish manager before giving up
        logger.exception("Failed to reset subdevices to known states.")

    try:
        [[_], [unique_id]] = dish_manager_proxy.SetStandbyFPMode()
        result_events.wait_for_command_id(unique_id, timeout=8)
        dish_mode_events.wait_for_value(DishMode.STANDBY_FP, timeout=10)
    except RuntimeError:
        # request FP mode and allow the test to continue
        dish_manager_proxy.SetStandbyFPMode()
        dish_mode_events.get_queue_values()
    finally:
        remove_subscriptions(subscriptions)

    yield
