"""Tests to verify that dish manager monitors B5DC tango device attributes."""

import pytest
import tango


@pytest.mark.forked
@pytest.mark.parametrize(
    "attribute",
    [
        "rfcmfrequency",
        "rfcmplllock",
        "rfcmhattenuation",
        "rfcmvattenuation",
        "clkphotodiodecurrent",
        "hpolrfpowerin",
        "vpolrfpowerin",
        "hpolrfpowerout",
        "vpolrfpowerout",
        "rftemperature",
        "rfcmpsupcbtemperature",
    ],
)
def test_b5dc_attributes_are_readable_and_read_only(dish_manager_proxy, attribute) -> None:
    """Verify that all B5DC attributes exposed via DishManager are read-only."""
    b5dc_attribute_type = dish_manager_proxy.get_attribute_config(attribute).writable
    assert b5dc_attribute_type == tango.AttrWriteType.READ
    attribute_value = dish_manager_proxy.read_attribute(attribute).value
    assert attribute_value is not None


@pytest.mark.forked
def test_b5dc_attributes_updates(dish_manager_proxy, event_store_class):
    """Test that dish manager recieves b5dc attribute updates,
    the attribute used is rfcmPsuPcbTemperature.
    """
    event_store = event_store_class()
    default_rfcmPsuPcbTemperature_value = 0.0
    dish_manager_proxy.subscribe_event(
        "rfcmPsuPcbTemperature",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    event_store.get_queue_values()

    assert (
        dish_manager_proxy.read_attribute("rfcmPsuPcbTemperature").value
        != default_rfcmPsuPcbTemperature_value
    )
    assert dish_manager_proxy.rfcmPsuPcbTemperature != default_rfcmPsuPcbTemperature_value


@pytest.mark.forked
@pytest.mark.parametrize(
    "attr_name",
    [
        "rfcmfrequency",
        "rfcmplllock",
        "rfcmhattenuation",
        "rfcmvattenuation",
        "clkphotodiodecurrent",
        "hpolrfpowerin",
        "vpolrfpowerin",
        "hpolrfpowerout",
        "vpolrfpowerout",
        "rftemperature",
        "rfcmpsupcbtemperature",
    ],
)
def test_b5dc_emits_change_and_archive_events(dish_manager_proxy, attr_name, event_store_class):
    """Ensure B5DC attributes emit both CHANGE and ARCHIVE events."""
    change_store = event_store_class()
    archive_store = event_store_class()

    # Subscribe to CHANGE and ARCHIVE events
    sub_id_arch = dish_manager_proxy.subscribe_event(
        attr_name, tango.EventType.CHANGE_EVENT, change_store
    )
    sub_id_event = dish_manager_proxy.subscribe_event(
        attr_name, tango.EventType.ARCHIVE_EVENT, archive_store
    )

    assert change_store.get_queue_events()
    assert archive_store.get_queue_events()

    dish_manager_proxy.unsubscribe_event(sub_id_arch)
    dish_manager_proxy.unsubscribe_event(sub_id_event)
