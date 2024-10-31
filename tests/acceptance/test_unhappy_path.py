"""Test dish unhappy path."""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
    SPFOperatingMode,
    SPFRxOperatingMode,
)


# pylint:disable=unused-argument
@pytest.mark.acceptance
@pytest.mark.forked
def test_dish_handles_unhappy_path_in_command_execution(
    undo_raise_exceptions,
    event_store_class,
    dish_manager_proxy,
    spf_device_proxy,
    spfrx_device_proxy,
):
    """Test DishManager handles errors in SPFC and SPFRx"""
    progress_event_store = event_store_class()
    result_event_store = event_store_class()
    band_event_store = event_store_class()
    dish_mode_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "longRunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "configuredBand",
        tango.EventType.CHANGE_EVENT,
        band_event_store,
    )

    # transition through FP > OPERATE > LP
    # SetStandbyLPMode is the only command which fans out
    # to SPF and SPFRx devices: this allows us test the exception
    dish_manager_proxy.SetStandbyFPMode()
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=8)

    dish_manager_proxy.ConfigureBand1(True)
    band_event_store.wait_for_value(Band.B1, timeout=8)

    dish_manager_proxy.SetOperateMode()
    dish_mode_event_store.wait_for_value(DishMode.OPERATE, timeout=8)

    dish_manager_proxy.SetStandbyFPMode()
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=8)

    # Enable failure modes
    spf_device_proxy.raiseCmdException = True
    spfrx_device_proxy.raiseCmdException = True
    result_event_store.clear_queue()

    dish_manager_proxy.SetStandbyLPMode()

    progress_msg = "SPFRX device failed executing SetStandbyMode command with ID"
    progress_event_store.wait_for_progress_update(progress_msg, timeout=5)

    result_event_store = result_event_store.get_queue_values(timeout=5)
    # filter out only the event values
    result_event_store = [evt_vals[1] for evt_vals in result_event_store]
    # join all unique ids and exceptions as one string
    unique_ids = "".join([evts[0] for evts in result_event_store])
    raised_exceptions = "".join([evts[1] for evts in result_event_store])
    result_event_store = [unique_ids, raised_exceptions]

    expected_lrc_result = [
        ("SPF_SetStandbyLPMode", "Exception: SetStandbyLPMode raised an exception"),
        ("SPFRX_SetStandbyMode", "Exception: SetStandbyMode raised an exception"),
    ]
    for unique_id, exc_raised in expected_lrc_result:
        assert unique_id in result_event_store[0]
        assert exc_raised in result_event_store[1]

    # check that the mode transition to LP mode did not happen on dish manager, spf and spfrx
    assert dish_manager_proxy.dishMode == DishMode.UNKNOWN
    assert spf_device_proxy.operatingMode == SPFOperatingMode.OPERATE
    assert spfrx_device_proxy.operatingMode == SPFRxOperatingMode.OPERATE
