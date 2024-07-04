"""Unit tests for input validation of of track table."""

from time import time

import pytest

from ska_mid_dish_manager.utils.ska_epoch_to_tai import get_tai_timestamp_from_unix_s
from ska_mid_dish_manager.utils.track_table_input_validation import (
    TrackLoadTableFormatting,
    TrackTableTimestampError,
)

MAX_TRACK_LOAD_TABLE_SAMPLES = 50


# pylint:disable=attribute-defined-outside-init
@pytest.mark.unit
class TestTrackLoadTableFormatting:
    """Tests for TrackLoadTableFormatting"""

    def setup_method(self):
        """Set up context"""
        self.future_time_s = 5
        self.track_table_formatter = TrackLoadTableFormatting()

    def test_track_table_input_happy(self):
        """Test happy path when length and future time is appropriate"""
        offset_s = 1.0
        time_future_unix = time() + self.future_time_s + offset_s
        time_future_tai = get_tai_timestamp_from_unix_s(time_future_unix)
        table = [time_future_tai, 2.0, 3.0]
        self.track_table_formatter.check_track_table_input_valid(table, self.future_time_s)

    def test_track_table_input_invalid_time(self):
        """Test when future time check fails"""
        offset_s = -0.5
        time_future_unix = time() + self.future_time_s + offset_s
        time_future_tai = get_tai_timestamp_from_unix_s(time_future_unix)
        table = [time_future_tai, 2.0, 3.0]
        with pytest.raises(TrackTableTimestampError):
            self.track_table_formatter.check_track_table_input_valid(table, self.future_time_s)

    def test_track_table_input_invalid_length(self):
        """Test when table length is invalid"""
        offset_s = -0.1
        time_future_unix = time() + self.future_time_s + offset_s
        table = [time_future_unix, 2.0, 3.0, 4.0]
        with pytest.raises(ValueError):
            self.track_table_formatter.check_track_table_input_valid(table, self.future_time_s)

    def test_track_table_input_empty_list(self):
        """Test when table length is empty"""
        table = []
        self.track_table_formatter.check_track_table_input_valid(table, self.future_time_s)

    def test_track_table_time_monotonically_inc(self):
        """Test when time elements are monotonically increasing"""
        track_table = []
        time_future_unix = time() + 30

        # generate 5 samples with 1 second increment and dummy el/az
        for n in range(0, 5):
            timestamp_in_sec = time_future_unix + n
            tai_time = get_tai_timestamp_from_unix_s(timestamp_in_sec)
            track_table.extend([tai_time, 0, 0])

        # add entry with time less than previous entry
        track_table.extend([tai_time - 1, 0, 0])

        with pytest.raises(TrackTableTimestampError):
            self.track_table_formatter.check_track_table_input_valid(
                track_table, self.future_time_s
            )
