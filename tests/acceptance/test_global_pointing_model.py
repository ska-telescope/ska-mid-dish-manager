"""Test Static Pointing Model."""

from typing import Any

import pytest
import tango

from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.fixture(autouse=True)
def reset_global_pointing(dish_manager_proxy: tango.DeviceProxy):
    yield
    # restore defaults
    dish_manager_proxy.TrackLoadStaticOff([0.0, 0.0])


@pytest.mark.fast
@pytest.mark.acceptance
def test_track_load_static_off(
    dish_manager_proxy: tango.DeviceProxy, event_store_class: Any
) -> None:
    """Test TrackLoadStaticOff command."""
    write_values = [20.1, 0.5]

    model_event_store = event_store_class()
    status_event_store = event_store_class()
    attr_cb_mapping = {
        "actStaticOffsetValueXel": model_event_store,
        "actStaticOffsetValueEl": model_event_store,
        "Status": status_event_store,
    }

    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    dish_manager_proxy.TrackLoadStaticOff(write_values)

    expected_progress_updates = [
        "Fanned out commands: DS.TrackLoadStaticOff",
        "Awaiting DS actstaticoffsetvaluexel, actstaticoffsetvalueel change to "
        f"{write_values[0]}, {write_values[1]}",
        "Awaiting actstaticoffsetvaluexel, actstaticoffsetvalueel change to "
        f"{write_values[0]}, {write_values[1]}",
        f"DS actstaticoffsetvaluexel changed to {write_values[0]}",
        f"DS actstaticoffsetvalueel changed to {write_values[1]}",
        "TrackLoadStaticOff completed",
    ]

    events = status_event_store.wait_for_progress_update(expected_progress_updates[-1], timeout=30)

    events_string = "".join([str(event.attr_value.value) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store.
    for message in expected_progress_updates:
        assert message in events_string

    model_event_store.wait_for_value(write_values[0], timeout=7)
    model_event_store.wait_for_value(write_values[1], timeout=7)

    remove_subscriptions(subscriptions)
