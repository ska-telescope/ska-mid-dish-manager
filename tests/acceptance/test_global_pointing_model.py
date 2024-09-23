"""Test Static Pointing Model."""

import json
from pathlib import Path
from typing import Any

import pytest
import tango


@pytest.mark.acceptance
@pytest.mark.forked
def test_track_load_static_off(
    dish_manager_proxy: tango.DeviceProxy, event_store_class: Any
) -> None:
    """Test TrackLoadStaticOff command."""
    write_values = [20.1, 0.5]

    model_event_store = event_store_class()
    progress_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "actStaticOffsetValueXel", tango.EventType.CHANGE_EVENT, model_event_store
    )
    dish_manager_proxy.subscribe_event(
        "actStaticOffsetValueEl", tango.EventType.CHANGE_EVENT, model_event_store
    )
    dish_manager_proxy.subscribe_event(
        "longrunningCommandProgress", tango.EventType.CHANGE_EVENT, progress_event_store
    )

    dish_manager_proxy.TrackLoadStaticOff(write_values)

    expected_progress_updates = [
        "TrackLoadStaticOff called on DS",
        "Awaiting DS actstaticoffsetvaluexel, actstaticoffsetvalueel change to "
        f"{write_values[0]}, {write_values[1]}",
        "Awaiting actstaticoffsetvaluexel, actstaticoffsetvalueel change to "
        f"{write_values[0]}, {write_values[1]}",
        f"DS actstaticoffsetvaluexel changed to {write_values[0]}",
        f"DS actstaticoffsetvalueel changed to {write_values[1]}",
        "TrackLoadStaticOff completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store.
    for message in expected_progress_updates:
        assert message in events_string

    model_event_store.wait_for_value(write_values[0], timeout=7)
    model_event_store.wait_for_value(write_values[1], timeout=7)
