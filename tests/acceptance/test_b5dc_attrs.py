"""Tests to verify that dish manager monitors B5DC tango device attributes."""

import pytest
import tango


@pytest.mark.acceptance
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


@pytest.mark.acceptance
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
    assert change_store.wait_for_n_events(1, timeout=6)
    assert archive_store.wait_for_n_events(1, timeout=6)

    dish_manager_proxy.unsubscribe_event(sub_id_arch)
    dish_manager_proxy.unsubscribe_event(sub_id_event)
