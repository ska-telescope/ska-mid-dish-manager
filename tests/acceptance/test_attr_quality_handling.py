"""Test dish manager handles and publishes change events on attribute quality update."""

import pytest
from tango import AttrQuality

from tests.utils import EventStore, remove_subscriptions, setup_subscriptions


@pytest.mark.acceptance
def test_quality_state_mirroring(dish_manager_proxy, spfrx_device_proxy):
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
