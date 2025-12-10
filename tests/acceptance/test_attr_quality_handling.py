"""Test dish manager handles and publishes change events on attribute quality update."""

import itertools
import pytest
from tango import AttrQuality

from tests.utils import EventStore, remove_subscriptions, setup_subscriptions


@pytest.mark.skip(reason="It was never enabled - fix in a separate MR")
@pytest.mark.acceptance
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

    # Setting up subscriptions to the attrs forces them to be VALID,
    # therefore set them invalid
    spfrx_device_proxy.SetAttenuation1PolVYQuality(AttrQuality.ATTR_INVALID)
    spfrx_event_store.wait_for_quality(AttrQuality.ATTR_INVALID)
    dm_event_store.wait_for_quality(AttrQuality.ATTR_INVALID)

    spfrx_device_proxy.SetAttenuation1PolVYQuality(AttrQuality.ATTR_VALID)
    spfrx_event_store.wait_for_quality(AttrQuality.ATTR_VALID)
    dm_event_store.wait_for_quality(AttrQuality.ATTR_VALID)

    remove_subscriptions(spfrx_subsciptions)
    remove_subscriptions(dm_subscriptions)
