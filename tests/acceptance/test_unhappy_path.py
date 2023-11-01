"""Test dish unhappy path."""
import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode, SPFOperatingMode


# pylint:disable=unused-argument
@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_dish_handles_unhappy_path_in_command_execution(
    undo_raise_exceptions, event_store_class, dish_manager_proxy, spf_device_proxy
):
    """Test SetStandbyFP command fails when an exception is raised in sub device"""
    # Intentionally raising an exception on the SPF device
    spf_device_proxy.raiseCmdException = True

    status_event_store = event_store_class()
    progress_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "longRunningCommandStatus",
        tango.EventType.CHANGE_EVENT,
        status_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    # Transition to FP mode.
    dish_manager_proxy.SetStandbyFPMode()
    progress_msg = "SPF device failed executing SetOperateMode command with ID"
    progress_event_store.wait_for_progress_update(progress_msg, timeout=10)

    status_events = status_event_store.get_queue_values()
    # e.g. event value
    # ('1698789854.0524402_25226166262345_SetStandbyFPMode','IN_PROGRESS',
    #  '1698790594.4820323_175005265068885_SetStandbyFPMode','IN_PROGRESS',
    #  '1698790594.482619_219526656679224_SPF_SetOperateMode','FAILED',
    #  '1698790594.4827623_67107500288526_DS_SetStandbyFPMode','COMPLETED')
    last_status_event_value = status_events[-1][-1]
    assert "FAILED" in last_status_event_value

    # check that the mode transition to FP mode did not happen on dish manager and spf
    assert spf_device_proxy.operatingMode == SPFOperatingMode.STANDBY_LP
    assert dish_manager_proxy.dishMode == DishMode.UNKNOWN
