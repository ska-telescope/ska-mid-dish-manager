"""Test client can subscribe to archive events."""

import pytest
import tango


@pytest.mark.unit
@pytest.mark.forked
def test_client_receives_archive_event(dish_manager_resources, event_store):
    """Verify archive events get pushed to the event store."""
    device_proxy, _ = dish_manager_resources
    device_proxy.subscribe_event(
        "dishMode",
        tango.EventType.ARCHIVE_EVENT,
        event_store,
    )

    assert event_store.get_queue_events()
