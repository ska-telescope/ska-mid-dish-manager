"""Test dish unhappy path."""

import pytest
from ska_mid_dish_simulators.sim_enums import (
    Band,
    SPFOperatingMode,
    SPFRxOperatingMode,
)

from ska_mid_dish_manager.models.dish_enums import DishMode
from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.mark.acceptance
def test_dish_handles_unhappy_path_in_command_execution(
    undo_raise_exceptions,
    event_store_class,
    dish_manager_proxy,
    spf_device_proxy,
    spfrx_device_proxy,
):
    """Test DishManager handles errors in SPFC and SPFRx."""
    status_event_store = event_store_class()
    result_event_store = event_store_class()
    band_event_store = event_store_class()
    dish_mode_event_store = event_store_class()
    attr_cb_mapping = {
        "dishMode": dish_mode_event_store,
        "configuredBand": band_event_store,
        "longRunningCommandResult": result_event_store,
        "Status": status_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    # transition through FP > OPERATE > LP
    # SetStandbyLPMode is the only command which fans out
    # to SPF and SPFRx devices: this allows us test the exception
    dish_manager_proxy.ConfigureBand1(True)
    band_event_store.wait_for_value(Band.B1, timeout=8)

    # Await auto transition to OPERATE following band config
    dish_mode_event_store.wait_for_value(DishMode.OPERATE, timeout=30)

    dish_manager_proxy.SetStandbyFPMode()
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=8)

    # Enable failure modes
    spf_device_proxy.raiseCmdException = True
    spfrx_device_proxy.raiseCmdException = True
    result_event_store.clear_queue()
    status_event_store.clear_queue()

    dish_manager_proxy.SetStandbyLPMode()

    progress_msg = "SetStandbyLPMode failed Exception:"
    status_event_store.wait_for_progress_update(progress_msg, timeout=5)

    result_event_store = result_event_store.get_queue_values(timeout=5)
    # e.g ['[0, "SetStandbyFPMode completed"]', '[3, "SetStandbyLPMode failed"]', ...]
    lrc_result_msgs = [event[1][1] for event in result_event_store]
    expected_result_message = lrc_result_msgs[-1]
    assert "SetStandbyLPMode failed" in expected_result_message, lrc_result_msgs

    # check that the mode transition to LP mode did not happen on dish manager, spf and spfrx
    assert dish_manager_proxy.dishMode == DishMode.STANDBY_FP
    assert spf_device_proxy.operatingMode == SPFOperatingMode.OPERATE
    assert spfrx_device_proxy.operatingMode == SPFRxOperatingMode.OPERATE

    remove_subscriptions(subscriptions)
