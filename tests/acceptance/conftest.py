"""Fixtures for running ska-mid-dish-manager acceptance tests."""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    SPFOperatingMode,
    SPFRxOperatingMode,
)


@pytest.fixture
def undo_raise_exceptions(spf_device_proxy, spfrx_device_proxy):
    """Undo any updates to raiseCmdException in SPF and SPFRx."""
    yield
    spf_device_proxy.raiseCmdException = False
    spfrx_device_proxy.raiseCmdException = False


@pytest.fixture(autouse=True)
def setup_and_teardown(
    event_store,
    dish_manager_proxy,
    ds_device_proxy,
    spf_device_proxy,
    spfrx_device_proxy,
):
    """Reset the tango devices to a fresh state before each test."""
    # this wait is very important for our AUTOMATED tests!!!
    # wait for task status updates to finish before resetting the
    # sub devices to a clean state for the next test. Reasons are:
    # [*] your command map may never evaluate true for the
    # awaited value to report the final task status of the LRC.
    # [*] the base classes needs this final task status to allow the
    # subsequently issued commands to be moved from queued to in progress

    # another approach will be to ensure that all tests check the
    # command status for every issued command as part of its assert
    event_store.get_queue_events(timeout=5)

    spf_device_proxy.subscribe_event(
        "operatingMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    spfrx_device_proxy.subscribe_event(
        "operatingMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    ds_device_proxy.subscribe_event(
        "operatingMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    # clear the queue before the resets start
    event_store.clear_queue()

    try:
        spf_device_proxy.ResetToDefault()
        assert event_store.wait_for_value(SPFOperatingMode.STANDBY_LP, timeout=10)

        spfrx_device_proxy.ResetToDefault()
        assert event_store.wait_for_value(SPFRxOperatingMode.STANDBY, timeout=10)

        if ds_device_proxy.operatingMode != DSOperatingMode.STANDBY_FP:
            # go to FP ...
            ds_device_proxy.SetStandbyFPMode()
            assert event_store.wait_for_value(DSOperatingMode.STANDBY_FP, timeout=30)
        # ... and then to LP
        ds_device_proxy.SetStandbyLPMode()
        assert event_store.wait_for_value(DSOperatingMode.STANDBY_LP, timeout=30)
    except (RuntimeError, AssertionError):
        # if expected events are not received after reset, allow
        # SyncComponentStates to be called before giving up
        pass

    event_store.clear_queue()
    dish_manager_proxy.SyncComponentStates()

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    try:
        event_store.wait_for_value(DishMode.STANDBY_LP, timeout=30)
    except RuntimeError as err:
        component_states = dish_manager_proxy.GetComponentStates()
        raise RuntimeError(f"DishManager not in STANDBY_LP:\n {component_states}\n") from err

    yield
