"""Fixtures for running ska-mid-dish-manager acceptance tests."""

import logging
import os

import pytest
import tango
from ska_mid_dish_utils.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    DSPowerState,
)

from ska_mid_dish_manager.models.constants import DEFAULT_ACTION_TIMEOUT_S
from tests.utils import EventPrinter, TrackedDevice, remove_subscriptions, setup_subscriptions

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


@pytest.fixture(scope="package")
def dish_manager_proxy(dish_manager_device_fqdn):
    dev_proxy = tango.DeviceProxy(dish_manager_device_fqdn)
    # increase client request timeout to 5 seconds
    dev_proxy.set_timeout_millis(5000)
    return dev_proxy


@pytest.fixture(scope="package")
def ds_device_proxy(ds_device_fqdn):
    dev_proxy = tango.DeviceProxy(ds_device_fqdn)
    # increase client request timeout to 5 seconds
    dev_proxy.set_timeout_millis(5000)
    return dev_proxy


@pytest.fixture(scope="package")
def b5dc_device_proxy(b5dc_device_fqdn):
    dev_proxy = tango.DeviceProxy(b5dc_device_fqdn)
    # increase client request timeout to 5 seconds
    dev_proxy.set_timeout_millis(5000)
    return dev_proxy


@pytest.fixture(scope="package")
def spf_device_proxy(spf_device_fqdn):
    return tango.DeviceProxy(spf_device_fqdn)


@pytest.fixture(scope="package")
def spfrx_device_proxy(spfrx_device_fqdn):
    return tango.DeviceProxy(spfrx_device_fqdn)


@pytest.fixture(scope="package")
def wms_device_proxy(wms_device_fqdn):
    return tango.DeviceProxy(wms_device_fqdn)


@pytest.fixture
def monitor_tango_servers(request: pytest.FixtureRequest, dish_manager_proxy, ds_device_proxy):
    event_files_dir = request.config.getoption("--event-storage-files-path")
    if event_files_dir is None:
        yield None
        return

    if not os.path.exists(event_files_dir):
        os.makedirs(event_files_dir)

    file_name = ".".join((f"events_{request.node.name}", "txt"))
    file_path = os.path.join(event_files_dir, file_name)

    dm_tracker = TrackedDevice(
        dish_manager_proxy,
        (
            "dishmode",
            "capturing",
            "healthstate",
            "pointingstate",
            "b1capabilitystate",
            "b2capabilitystate",
            "b3capabilitystate",
            "b4capabilitystate",
            "b5acapabilitystate",
            "b5bcapabilitystate",
            "achievedtargetlock",
            "dsccmdauth",
            "dscctrlstate",
            "configuretargetlock",
            "achievedpointing",
            "configuredband",
            "spfconnectionstate",
            "spfrxconnectionstate",
            "dsconnectionstate",
            "b5dcconnectionstate",
            "longrunningcommandstatus",
            "longrunningcommandresult",
            "longrunningcommandprogress",
        ),
    )
    ds_tracker = TrackedDevice(
        ds_device_proxy,
        (
            "operatingMode",
            "powerState",
            "healthState",
            "pointingState",
            "indexerPosition",
            "achievedPointing",
            "achievedTargetLock",
            "dscCmdAuth",
            "dscCtrlState",
            "configureTargetLock",
        ),
    )

    event_printer = EventPrinter(file_path, (dm_tracker, ds_tracker))
    with event_printer:
        with open(file_path, "a", encoding="utf-8") as open_file:
            open_file.write("\n\nEvents set up, test starting\n")
        yield


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
            ds_device_proxy.TakeAuthority()
            # wait 10s for the horn to go off
            dish_mode_events.get_queue_values(timeout=30)
            dish_manager_proxy.SetStowMode()
            dish_mode_events.wait_for_value(DishMode.STOW, timeout=120)

        if ds_device_proxy.operatingMode != DSOperatingMode.STANDBY:
            ds_device_proxy.SetStandbyMode()
            op_mode_events.wait_for_value(DSOperatingMode.STANDBY, timeout=30)
            power_state_events.wait_for_value(DSPowerState.LOW_POWER, timeout=30)
        # go to FP
        ds_device_proxy.SetPowerMode([0.0, 14.7])
        power_state_events.wait_for_value(DSPowerState.FULL_POWER, timeout=30)

    except (RuntimeError, AssertionError):
        pass

    if dish_manager_proxy.dishMode != DishMode.STANDBY_FP:
        try:
            dish_manager_proxy.SetStandbyFPMode()
            dish_mode_events.wait_for_value(DishMode.STANDBY_FP, timeout=60)
        except (RuntimeError, tango.DevFailed):
            logger.debug("DishManager commands: %s", dish_manager_proxy.longrunningcommandstatus)
            logger.debug("DSManager commands: %s", ds_device_proxy.longrunningcommandstatus)
            logger.debug("\n\nDM component state: %s\n\n", dish_manager_proxy.GetComponentStates())
            remove_subscriptions(subscriptions)
            raise

    remove_subscriptions(subscriptions)

    yield
