"""Test ConfigureBand2"""
import pytest
import tango
from ska_control_model import TaskStatus

from ska_mid_dish_manager.models.dish_enums import Band, DishMode
from tests.utils import set_configuredBand_b1


# pylint: disable=too-many-locals
@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_configure_band_2(
    event_store_class, dish_manager_proxy, ds_device_proxy, spf_device_proxy, spfrx_device_proxy
):
    """Test ConfigureBand2"""
    main_event_store = event_store_class()
    progress_event_store = event_store_class()
    dishmode_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dishmode_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    attributes = ["longrunningcommandresult", "configuredBand"]
    for attribute_name in attributes:
        dish_manager_proxy.subscribe_event(
            attribute_name,
            tango.EventType.CHANGE_EVENT,
            main_event_store,
        )

    [[_], [unique_id]] = dish_manager_proxy.SetStandbyFPMode()
    main_event_store.wait_for_command_id(unique_id, timeout=8)
    assert dish_manager_proxy.dishMode == DishMode.STANDBY_FP
    # make sure configureBand is not B2
    set_configuredBand_b1(
        dish_manager_proxy, ds_device_proxy, spf_device_proxy, spfrx_device_proxy
    )
    main_event_store.clear_queue()
    progress_event_store.clear_queue()
    dishmode_event_store.clear_queue()

    [[_], [unique_id]] = dish_manager_proxy.ConfigureBand2(False)

    dishmode_event_store.wait_for_value(DishMode.CONFIG, timeout=9)
    main_event_store.wait_for_command_id(unique_id)

    assert dish_manager_proxy.configuredBand == Band.B2
    dishmode_event_store.wait_for_value(DishMode.STANDBY_FP)

    # Do it again to check result
    [[task_status], [result]] = dish_manager_proxy.ConfigureBand2(False)
    assert task_status == TaskStatus.COMPLETED
    assert result == "Already in band B2"

    expected_progress_updates = [
        "SetIndexPosition called on DS",
        "ConfigureBand2 called on SPFRx, ID",
        "Awaiting configuredband change to B2",
        "ConfigureBand2 completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store.
    for message in expected_progress_updates:
        assert message in events_string
