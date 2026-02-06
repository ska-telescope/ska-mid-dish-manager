"""Test CapabilityState."""

import pytest

from ska_mid_dish_manager.models.dish_enums import Band, CapabilityStates, DishMode
from tests.utils import remove_subscriptions, setup_subscriptions


# classifying as fast to balance the total run time across parallel jobs
@pytest.mark.fast
@pytest.mark.acceptance
def test_capability_state_b1(monitor_tango_servers, event_store_class, dish_manager_proxy):
    """Test transition on CapabilityState b1."""
    main_event_store = event_store_class()
    cap_state_event_store = event_store_class()
    attr_cb_mapping = {
        "configuredBand": main_event_store,
        "b1CapabilityState": cap_state_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    # ensure current band is not B1
    dish_manager_proxy.ConfigureBand2(True)
    main_event_store.wait_for_value(Band.B2, timeout=10)
    cap_state_event_store.clear_queue()

    dish_manager_proxy.ConfigureBand1(True)

    cap_state_event_store.wait_for_value(CapabilityStates.CONFIGURING, timeout=10)
    cap_state_event_store.wait_for_value(CapabilityStates.OPERATE_FULL, timeout=10)

    assert dish_manager_proxy.dishMode == DishMode.OPERATE

    remove_subscriptions(subscriptions)
