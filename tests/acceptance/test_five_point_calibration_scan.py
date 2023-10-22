"""Tests for the five point calibration scan."""
import pytest
import tango


@pytest.mark.acceptance
@pytest.mark.forked
def test_program_track_table(event_store_class, dish_manager_proxy):
    """Tests the program track attribute."""

    attr_event_store = event_store_class()
    write_values = [12345, 100, 100, 123456, 101, 102]

    dish_manager_proxy.subscribe_event(
        "programTrackTable", tango.EventType.CHANGE_EVENT, attr_event_store
    )
    dish_manager_proxy.programTrackTable = write_values
    attr_event_store.wait_for_value(write_values, timeout=7)
