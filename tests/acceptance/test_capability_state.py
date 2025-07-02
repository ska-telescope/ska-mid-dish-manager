"""Test CapabilityState."""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import CapabilityStates, DishMode


@pytest.mark.acceptance
@pytest.mark.forked
def test_capability_state_b1(monitor_tango_servers, event_store_class, dish_manager_proxy):
    """Test transition on CapabilityState b1."""
    main_event_store = event_store_class()
    cap_state_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )
    dish_manager_proxy.subscribe_event(
        "b1CapabilityState",
        tango.EventType.CHANGE_EVENT,
        cap_state_event_store,
    )
    # on subscription the first event is CapabilityStates.STANDBY
    # clear out the queue before command executes
    cap_state_event_store.clear_queue()
    dish_manager_proxy.SetStandbyFPMode()

    cap_state_event_store.wait_for_value(CapabilityStates.STANDBY, timeout=10)
    main_event_store.wait_for_value(DishMode.STANDBY_FP)

    assert dish_manager_proxy.b1CapabilityState == CapabilityStates.STANDBY
    assert dish_manager_proxy.dishMode == DishMode.STANDBY_FP
