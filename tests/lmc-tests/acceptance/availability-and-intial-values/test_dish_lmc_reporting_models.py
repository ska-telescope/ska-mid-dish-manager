"""Verify that dish_lmc supports reading attributes in 3 different ways
(R.LMC.FMON.26)
"""

import pytest

import tango


@pytest.mark.acceptance
def test_dish_manager_supports_all_reporting_models(dish_manager, dish_manager_event_store):
    """Test that dish manager supports attribute reads on request and with events"""
    dish_mode = dish_manager.dishMode.value

    # On request
    assert dish_mode == dish_manager.dishMode.value

    # change events
    dish_manager.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        dish_manager_event_store,
    )
    dish_mode_events = dish_manager_event_store.get_queue_values()
    # On event subscription the first event data is the current
    # attribute value. Confirm this with earlier retrieved value
    dish_mode_ch_event_reading = dish_mode_events[0][1]
    assert dish_mode == dish_mode_ch_event_reading


@pytest.mark.acceptance
@pytest.mark.parametrize("domain", ["001"])
@pytest.mark.parametrize("family_member", ["lmc/ds_simulator", "spf/simulator", "spfrx/simulator"])
def test_sub_elements_support_all_reporting_models(domain, family_member):
    """Test that dish structure, spf and spfrx devices
    support attribute reads on request and with events"""
    tango_device_proxy = tango.DeviceProxy(f"ska{domain}/{family_member}")
    operating_mode = tango_device_proxy.operatingMode.value
    evt_ids = []

    # On request
    assert operating_mode == tango_device_proxy.read_attribute("operatingMode").value

    # change events
    cb = tango.utils.EventCallback()
    evt_ids.append(
        tango_device_proxy.subscribe_event("operatingMode", tango.EventType.CHANGE_EVENT, cb, [])
    )
    # On event subscription the first event data is the current
    # attribute value. Confirm this with earlier retrieved value
    operating_mode_ch_event_reading = cb.get_events()[0].attr_value.value
    assert operating_mode == operating_mode_ch_event_reading
