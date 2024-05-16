"""Test dish manager handles and publishes change events on attribute quality update"""
import itertools

import pytest
import tango
from tango import AttrQuality

from tests.utils import EventStore


@pytest.mark.parametrize(
    "qual_before,qual_after",
    list(
        itertools.permutations(
            [
                AttrQuality.ATTR_VALID,
                AttrQuality.ATTR_INVALID,
                AttrQuality.ATTR_CHANGING,
                AttrQuality.ATTR_WARNING,
                AttrQuality.ATTR_ALARM,
            ],
            2,
        )
    )[
        :10
    ],  # Just the first 10 for now
)
def test_transitions(dish_manager_proxy, spfrx_device_proxy, qual_before, qual_after):
    """Test quality of dishmanager exposed attribute mirrors the quality of the underlying
    subservient device attribute"""
    dm_event_store = EventStore()
    spfrx_event_store = EventStore()

    dish_manager_proxy.subscribe_event(
        "attenuationPolV",
        tango.EventType.CHANGE_EVENT,
        dm_event_store,
    )
    spfrx_device_proxy.subscribe_event(
        "attenuationPolV",
        tango.EventType.CHANGE_EVENT,
        spfrx_event_store,
    )
    spfrx_device_proxy.SetAttenuationPolVQuality(qual_before)
    spfrx_event_store.wait_for_quality(qual_before)
    dm_event_store.wait_for_quality(qual_before)

    spfrx_device_proxy.SetAttenuationPolVQuality(qual_after)
    spfrx_event_store.wait_for_quality(qual_after)
    dm_event_store.wait_for_quality(qual_after)
