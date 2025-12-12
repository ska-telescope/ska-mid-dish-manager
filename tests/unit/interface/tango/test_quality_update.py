"""Unit tests for the quality factor on change events."""

import itertools
import logging
from unittest.mock import MagicMock

import pytest
import tango
from tango import AttrQuality

LOGGER = logging.getLogger(__name__)


@pytest.mark.unit
@pytest.mark.forked
@pytest.mark.parametrize(
    "qual_before,qual_after",
    list(
        itertools.permutations(
            [
                AttrQuality.ATTR_VALID,
                AttrQuality.ATTR_INVALID,
            ],
            2,
        )
    ),
)
def test_change(qual_before, qual_after, event_store_class, dish_manager_resources):
    """Test the change events on the dish manager cm level."""
    device_proxy, dish_manager_cm = dish_manager_resources
    event_store = event_store_class()
    device_proxy.subscribe_event(
        "attenuation1PolVY",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    dish_manager_cm._quality_state_callback("attenuation1polvy", qual_before)
    event_store.wait_for_quality(qual_before)
    dish_manager_cm._quality_state_callback("attenuation1polvy", qual_after)
    event_store.wait_for_quality(qual_after)


@pytest.mark.forked
def test_event_handling(event_store_class, dish_manager_resources):
    """Test the change events on the tango device cm level."""
    device_proxy, dish_manager_cm = dish_manager_resources
    spfrx_cm = dish_manager_cm.sub_component_managers["SPFRX"]

    event_store = event_store_class()
    device_proxy.subscribe_event(
        "attenuation1PolVY",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    valid_event = MagicMock()
    valid_event.attr_value = MagicMock()
    valid_event.attr_value.name = "attenuation1PolVY"
    valid_event.attr_value.quality = AttrQuality.ATTR_VALID
    valid_event.attr_value.value = 1000

    invalid_event = MagicMock()
    invalid_event.attr_value = MagicMock()
    invalid_event.attr_value.name = "attenuation1PolVY"
    invalid_event.attr_value.quality = AttrQuality.ATTR_INVALID
    invalid_event.attr_value.value = None

    spfrx_cm._update_state_from_event(valid_event)
    event_store.wait_for_quality(AttrQuality.ATTR_VALID)

    spfrx_cm._update_state_from_event(invalid_event)
    event_store.wait_for_quality(AttrQuality.ATTR_INVALID)

    spfrx_cm._update_state_from_event(valid_event)
    event_store.wait_for_quality(AttrQuality.ATTR_VALID)
