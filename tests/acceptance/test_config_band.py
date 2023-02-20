"""Test ConfigureBand2"""
from datetime import datetime, timedelta

import pytest
import tango
from ska_control_model import TaskStatus

from ska_mid_dish_manager.devices.test_devices.utils import set_configuredBand_b1
from ska_mid_dish_manager.models.dish_enums import Band, DishMode


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
@pytest.mark.skip()
def test_configure_band_2(event_store_class, dish_manager_proxy):
    """Test ConfigureBand2"""
    # make sure configureBand is not B2
    set_configuredBand_b1()

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

    main_event_store.clear_queue()

    [[_], [unique_id]] = dish_manager_proxy.SetStandbyFPMode()
    main_event_store.wait_for_command_id(unique_id, timeout=8)
    assert dish_manager_proxy.dishMode == DishMode.STANDBY_FP

    main_event_store.clear_queue()

    future_time = datetime.utcnow() + timedelta(days=1)
    [[_], [unique_id]] = dish_manager_proxy.ConfigureBand2(future_time.isoformat())
    dishmode_event_store.wait_for_value(DishMode.CONFIG)
    assert 0, dish_manager_proxy.longrunningcommandresult
    main_event_store.wait_for_command_id(unique_id)
    assert dish_manager_proxy.configuredBand == Band.B2
    dishmode_event_store.wait_for_value(DishMode.STANDBY_FP)

    # Do it again to check result
    [[task_status], [result]] = dish_manager_proxy.ConfigureBand2(future_time.isoformat())
    assert task_status == TaskStatus.COMPLETED
    assert result == "Already in band B2"

    expected_progress_updates = [
        "SetIndexPosition called on DS",
        "ConfigureBand2 called on SPFRx, ID",
        "Awaiting configuredband to transition to [B2]",
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
