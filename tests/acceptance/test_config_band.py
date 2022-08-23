"""Test ConfigureBand2"""
from datetime import datetime, timedelta

import pytest
import tango
from ska_tango_base.commands import TaskStatus

from ska_mid_dish_manager.devices.test_devices.utils import (
    set_configuredBand_b1,
    set_dish_manager_to_standby_lp,
)
from ska_mid_dish_manager.models.dish_enums import Band, DishMode


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_configure_band_2(event_store, dish_manager_proxy):
    """Test ConfigureBand2"""
    set_dish_manager_to_standby_lp(event_store, dish_manager_proxy)
    assert dish_manager_proxy.dishMode == DishMode.STANDBY_LP

    # make sure configureBand is not B2
    set_configuredBand_b1()

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    dish_manager_proxy.subscribe_event(
        "longrunningcommandresult",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    dish_manager_proxy.subscribe_event(
        "configuredBand",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    event_store.clear_queue()

    [[_], [unique_id]] = dish_manager_proxy.SetStandbyFPMode()
    event_store.wait_for_command_id(unique_id, timeout=8)
    assert dish_manager_proxy.dishMode == DishMode.STANDBY_FP

    event_store.clear_queue()

    future_time = datetime.utcnow() + timedelta(days=1)
    [[_], [unique_id]] = dish_manager_proxy.ConfigureBand2(
        future_time.isoformat()
    )
    event_store.wait_for_command_id(unique_id)
    assert dish_manager_proxy.configuredBand == Band.B2

    # Do it again to check result
    [[task_status], [result]] = dish_manager_proxy.ConfigureBand2(
        future_time.isoformat()
    )
    assert task_status == TaskStatus.COMPLETED
    assert result == "Already in band B2"
