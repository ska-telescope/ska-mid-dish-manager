"""Test dish manager handles and publishes change events on attribute quality update."""

import itertools

import pytest
from tango import AttrQuality

from tests.utils import EventStore, remove_subscriptions, setup_subscriptions


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
    )[:10],  # Just the first 10 for now
)
def test_transitions(dish_manager_proxy, spfrx_device_proxy, qual_before, qual_after):
    """Test quality of dishmanager exposed attribute mirrors the quality of the underlying
    subservient device attribute.
    """
    dm_event_store = EventStore()
    spfrx_event_store = EventStore()
    spfrx_subsciptions = setup_subscriptions(
        spfrx_device_proxy, {"attenuation1PolV/Y": spfrx_event_store}
    )
    dm_subscriptions = setup_subscriptions(
        dish_manager_proxy, {"attenuation1PolV/Y": dm_event_store}
    )

    spfrx_device_proxy.SetAttenuation1PolVYQuality(qual_before)
    spfrx_event_store.wait_for_quality(qual_before)
    dm_event_store.wait_for_quality(qual_before)

    spfrx_device_proxy.SetAttenuation1PolVYQuality(qual_after)
    spfrx_event_store.wait_for_quality(qual_after)
    dm_event_store.wait_for_quality(qual_after)

    remove_subscriptions(spfrx_subsciptions)
    remove_subscriptions(dm_subscriptions)
