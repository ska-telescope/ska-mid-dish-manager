"""Unit test for lastCommandInvoked attribute."""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import (
    DishMode,
    DSOperatingMode,
    SPFOperatingMode,
)


@pytest.mark.unit
@pytest.mark.forked
def test_last_command_invoked(
    dish_manager_resources,
    event_store_class,
):
    """Test lastCommandInvoked attribute."""
    device_proxy, dish_manager_cm = dish_manager_resources
    ds_cm = dish_manager_cm.sub_component_managers["DS"]
    spf_cm = dish_manager_cm.sub_component_managers["SPF"]

    main_event_store = event_store_class()
    last_command_invoked_event_store = event_store_class()

    device_proxy.subscribe_event(
        "lastCommandInvoked",
        tango.EventType.CHANGE_EVENT,
        last_command_invoked_event_store,
    )
    last_command_invoked_event_store.clear_queue()

    device_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )

    # Force dishManager dishMode to go to STANDBY_FP (mode change)
    device_proxy.SetStandbyFPMode()
    ds_cm._update_component_state(operatingmode=DSOperatingMode.STANDBY_FP)
    spf_cm._update_component_state(operatingmode=SPFOperatingMode.OPERATE)
    main_event_store.wait_for_value(DishMode.STANDBY_FP)

    evts = last_command_invoked_event_store.wait_for_n_events(1)
    recorded_timestamp, recorded_cmd = evts[0].attr_value.value
    mode_invoked_time, commanded_name = device_proxy.lastCommandInvoked

    assert commanded_name == recorded_cmd
    assert mode_invoked_time == recorded_timestamp

    # Force a 1s wait so that the next command time is different (Consievably)
    last_command_invoked_event_store.wait_for_n_events(1)
    # Call SetKValue (non-mode change)
    device_proxy.SetKValue(15)
    kvalue_command_invoked_time, commanded_name = device_proxy.lastCommandInvoked
    # Make sure time has advanced (Indirectly greater than 0.0)
    assert kvalue_command_invoked_time > mode_invoked_time
    assert commanded_name == "SetKValue"
