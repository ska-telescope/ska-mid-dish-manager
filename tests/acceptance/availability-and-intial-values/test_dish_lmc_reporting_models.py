# flake8: noqa: E501
"""Verify that dish_lmc supports reading attributes in 3 different ways
(R.LMC.FMON.26)
"""


import time

import pytest
import tango


def test_dish_manager_supports_all_reporting_models(
    dish_manager, dish_manager_event_store
):
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


@pytest.mark.parametrize("domain", ["0001"])
@pytest.mark.parametrize(
    "family_member", ["lmc/ds_simulator", "spf/simulator", "spfrx/simulator"]
)
def test_sub_elements_support_all_reporting_models(domain, family_member):
    """Test that dish structure, spf and spfrx devices
    support attribute reads on request and with events"""
    tango_device_proxy = tango.DeviceProxy(f"mid_d{domain}/{family_member}")
    operating_mode = tango_device_proxy.operatingMode.value
    evt_ids = []

    # On request
    assert (
        operating_mode
        == tango_device_proxy.read_attribute("operatingMode").value
    )

    # change events
    cb = tango.utils.EventCallback()
    evt_ids.append(
        tango_device_proxy.subscribe_event(
            "operatingMode", tango.EventType.CHANGE_EVENT, cb, []
        )
    )
    # On event subscription the first event data is the current
    # attribute value. Confirm this with earlier retrieved value
    operating_mode_ch_event_reading = cb.get_events()[0].attr_value.value
    assert operating_mode == operating_mode_ch_event_reading

    # periodic events
    cb = tango.utils.EventCallback()
    evt_ids.append(
        tango_device_proxy.subscribe_event(
            "operatingMode", tango.EventType.PERIODIC_EVENT, cb, []
        )
    )
    previous_periodic_events = [
        evt_data.attr_value.value for evt_data in cb.get_events()[:]
    ]
    time.sleep(15)  # wait a while for more events to arrive
    current_periodic_events = [
        evt_data.attr_value.value for evt_data in cb.get_events()[:]
    ]
    # unsubscribe to events
    for evt_id in evt_ids:
        tango_device_proxy.unsubscribe_event(evt_id)

    # Verify that the events received keeps increasing
    assert len(previous_periodic_events) < len(current_periodic_events)
    # Verify that all the events are the same as the previous operatingMode reading
    assert all(
        operating_mode_reading == operating_mode
        for operating_mode_reading in current_periodic_events
    ), current_periodic_events
