"""Test client can subscribe to alarm events."""

import pytest
import tango

EXCLUDED_ATTRIBUTES = ["lrcProtocolVersions", "spectrumSample"]
MIN_ATTRIBUTE_COUNT = 125


@pytest.mark.unit
@pytest.mark.forked
def test_dish_manager_configured_alarm_events(dish_manager_resources, event_store_class):
    """Verify alarm events get pushed to the event store."""
    device_proxy, _ = dish_manager_resources
    attribute_names = device_proxy.get_attribute_list()
    assert len(attribute_names) >= MIN_ATTRIBUTE_COUNT, (
        f"Expected at least {MIN_ATTRIBUTE_COUNT} attributes, but found {len(attribute_names)}"
    )

    all_subsciptions_pass = True
    failed_attributes = []
    for attribute_name in attribute_names:
        if attribute_name in EXCLUDED_ATTRIBUTES:
            continue
        try:
            event_store = event_store_class()
            device_proxy.subscribe_event(
                attribute_name,
                tango.EventType.ALARM_EVENT,
                event_store,
            )
        except tango.DevFailed:
            all_subsciptions_pass = False
            failed_attributes.append(attribute_name)

    assert all_subsciptions_pass, (
        f"Not all attributes support ALARM_EVENT subscriptions: {failed_attributes}"
    )


@pytest.mark.unit
@pytest.mark.forked
def test_client_receives_alarm_event(dish_manager_resources, event_store_class):
    """Configure attribute alarm limits and verify ALARM_EVENT is received."""
    device_proxy, dish_manager_cm = dish_manager_resources
    event_store = event_store_class()

    attr_config = device_proxy.get_attribute_config("rfTemperature")
    attr_config.alarms.min_alarm = "-1"
    attr_config.alarms.max_alarm = "10"
    device_proxy.set_attribute_config(attr_config)

    subscription_id = device_proxy.subscribe_event(
        "rfTemperature",
        tango.EventType.ALARM_EVENT,
        event_store,
    )

    # check that attribute quality is valid
    assert device_proxy.read_attribute("rfTemperature").quality == tango.AttrQuality.ATTR_VALID

    # Simulate component state update to a value above max_alarm.
    dish_manager_cm._update_component_state(rftemperature=20.0)

    assert event_store.wait_for_n_events(1, timeout=6)

    # check that attribute quality is invalid
    assert device_proxy.read_attribute("rfTemperature").quality == tango.AttrQuality.ATTR_ALARM

    device_proxy.unsubscribe_event(subscription_id)


@pytest.mark.unit
@pytest.mark.forked
def test_client_receives_alarm_event_for_warning(dish_manager_resources, event_store_class):
    """Configure attribute alarm warning limits and verify ALARM_EVENT is received."""
    device_proxy, dish_manager_cm = dish_manager_resources
    event_store = event_store_class()

    attr_config = device_proxy.get_attribute_config("rfTemperature")
    attr_config.alarms.min_warning = "-1"
    attr_config.alarms.max_warning = "10"
    device_proxy.set_attribute_config(attr_config)

    subscription_id = device_proxy.subscribe_event(
        "rfTemperature",
        tango.EventType.ALARM_EVENT,
        event_store,
    )

    # check that attribute quality is valid
    assert device_proxy.read_attribute("rfTemperature").quality == tango.AttrQuality.ATTR_VALID

    # Simulate component state update to a value above max_warning.
    dish_manager_cm._update_component_state(rftemperature=20.0)

    assert event_store.wait_for_n_events(1, timeout=6)

    # check that attribute quality is in warning state
    assert device_proxy.read_attribute("rfTemperature").quality == tango.AttrQuality.ATTR_WARNING

    device_proxy.unsubscribe_event(subscription_id)
