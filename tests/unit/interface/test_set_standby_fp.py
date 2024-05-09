"""Unit tests for setstandby_fp command."""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode, DSOperatingMode, SPFOperatingMode


# pylint:disable=protected-access
@pytest.mark.unit
@pytest.mark.forked
def test_standby_fp(dish_manager_resources, event_store_class):
    """Execute tests"""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]

    dish_mode_event_store = event_store_class()
    progress_event_store = event_store_class()

    device_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_mode_event_store,
    )

    device_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    assert device_proxy.dishMode == DishMode.STANDBY_LP
    device_proxy.SetStandbyFPMode()
    # wait a bit before forcing the updates on the subcomponents
    dish_mode_event_store.get_queue_values()

    # transition subservient devices to FP mode and observe that
    # DishManager transitions dishMode to FP mode after all
    # subservient devices are in FP
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_FP)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    #  we can now expect dishMode to transition to STANDBY_FP
    dish_mode_event_store.wait_for_value(DishMode.STANDBY_FP)

    expected_progress_updates = [
        "SetStandbyFPMode called on DS",
        "SetOperateMode called on SPF",
        "Awaiting dishMode change to STANDBY_FP",
        "SetStandbyFPMode completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event.attr_value.value) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string
