"""Test dish manager handles and publishes change events on attribute quality update"""
import pytest
import tango

from tests.utils import EventStore


@pytest.mark.acceptance
def test_attribute_quality_handling_invalid(dish_manager_proxy, spfrx_device_proxy):
    """Test to ensure that dish manager attribute qualities mirror
    the invalid quality of the underlying attribute on the subservient device"""

    dm_event_store = EventStore()
    dm_subscription_id = dish_manager_proxy.subscribe_event(
        "attenuationPolV",
        tango.EventType.CHANGE_EVENT,
        dm_event_store,
    )
    dm_event_store.clear_queue()

    spfrx_event_store = EventStore()
    spfrx_subscription_id = spfrx_device_proxy.subscribe_event(
        "attenuationPolV",
        tango.EventType.CHANGE_EVENT,
        spfrx_event_store,
    )
    spfrx_event_store.clear_queue()

    # Sets the quality of the underlying attribute on SPFRx to invalid
    spfrx_device_proxy.SetAttenuationPolVQuality(1)

    dish_manager_event_queue = dm_event_store.get_queue_events()

    dish_manager_proxy.unsubscribe_event(dm_subscription_id)
    spfrx_device_proxy.unsubscribe_event(spfrx_subscription_id)

    assert dish_manager_event_queue[-1].attr_value.quality == tango.AttrQuality.ATTR_INVALID


# pylint: disable=too-many-locals,unused-argument
@pytest.mark.acceptance
def test_attribute_quality_handling_alarm(dish_manager_proxy, spfrx_device_proxy):
    """Test to ensure that dish manager attribute qualities mirror
    the alarm quality of the underlying attribute on the subservient device"""

    dm_event_store = EventStore()
    dm_subscription_id = dish_manager_proxy.subscribe_event(
        "attenuationPolV",
        tango.EventType.CHANGE_EVENT,
        dm_event_store,
    )
    dm_event_store.clear_queue()

    spfrx_event_store = EventStore()
    spfrx_subscription_id = spfrx_device_proxy.subscribe_event(
        "attenuationPolV",
        tango.EventType.CHANGE_EVENT,
        spfrx_event_store,
    )
    spfrx_event_store.clear_queue()

    # Sets the quality of the underlying attribute on SPFRx to alarm
    spfrx_device_proxy.SetAttenuationPolVQuality(2)

    dish_manager_event_queue = dm_event_store.get_queue_events()

    dish_manager_proxy.unsubscribe_event(dm_subscription_id)
    spfrx_device_proxy.unsubscribe_event(spfrx_subscription_id)

    assert dish_manager_event_queue[-1].attr_value.quality == tango.AttrQuality.ATTR_ALARM


# pylint: disable=too-many-locals,unused-argument
@pytest.mark.acceptance
def test_attribute_quality_handling_changing(dish_manager_proxy, spfrx_device_proxy):
    """Test to ensure that dish manager attribute qualities mirror
    the changing quality of the underlying attribute on the subservient device"""

    dm_event_store = EventStore()
    dm_subscription_id = dish_manager_proxy.subscribe_event(
        "attenuationPolV",
        tango.EventType.CHANGE_EVENT,
        dm_event_store,
    )
    dm_event_store.clear_queue()

    spfrx_event_store = EventStore()
    spfrx_subscription_id = spfrx_device_proxy.subscribe_event(
        "attenuationPolV",
        tango.EventType.CHANGE_EVENT,
        spfrx_event_store,
    )
    spfrx_event_store.clear_queue()

    # Sets the quality of the underlying attribute on SPFRx to changing
    spfrx_device_proxy.SetAttenuationPolVQuality(3)

    dish_manager_event_queue = dm_event_store.get_queue_events()

    dish_manager_proxy.unsubscribe_event(dm_subscription_id)
    spfrx_device_proxy.unsubscribe_event(spfrx_subscription_id)

    assert dish_manager_event_queue[-1].attr_value.quality == tango.AttrQuality.ATTR_CHANGING


# pylint: disable=too-many-locals,unused-argument
@pytest.mark.acceptance
def test_attribute_quality_handling_warning(dish_manager_proxy, spfrx_device_proxy):
    """Test to ensure that dish manager attribute qualities mirror
    the warning quality of the underlying attribute on the subservient device"""

    dm_event_store = EventStore()
    dm_subscription_id = dish_manager_proxy.subscribe_event(
        "attenuationPolV",
        tango.EventType.CHANGE_EVENT,
        dm_event_store,
    )
    dm_event_store.clear_queue()

    spfrx_event_store = EventStore()
    spfrx_subscription_id = spfrx_device_proxy.subscribe_event(
        "attenuationPolV",
        tango.EventType.CHANGE_EVENT,
        spfrx_event_store,
    )
    spfrx_event_store.clear_queue()

    # Sets the quality of the underlying attribute on SPFRx to warning
    spfrx_device_proxy.SetAttenuationPolVQuality(4)

    dish_manager_event_queue = dm_event_store.get_queue_events()

    dish_manager_proxy.unsubscribe_event(dm_subscription_id)
    spfrx_device_proxy.unsubscribe_event(spfrx_subscription_id)

    assert dish_manager_event_queue[-1].attr_value.quality == tango.AttrQuality.ATTR_WARNING
