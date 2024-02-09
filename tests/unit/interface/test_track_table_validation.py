"""Unit tests for input validation of of track table."""

from time import time
from unittest.mock import Mock

import pytest

from ska_mid_dish_manager.interface.input_validation import TrackLoadTableFormatting

MAX_TRACK_LOAD_TABLE_SAMPLES = 50


# pylint:disable=attribute-defined-outside-init
@pytest.mark.unit
@pytest.mark.forked
class TestTrackLoadTableFormatting:
    """Tests for TrackLoadTableFormatting"""

    def setup_method(self):
        """Set up context"""
        self.logger = Mock()
        self.future_time_s = 5
        self.track_table_formatter = TrackLoadTableFormatting(self.logger)

    def test_track_table_input_happy(self):
        """Test happy path when length and future time is appropriate"""
        offset_s = 0.1
        time_future_unix = time() * 1e3 + self.future_time_s + offset_s
        time_future_tai = self.track_table_formatter.get_tai_from_unix_s(time_future_unix)
        table = [time_future_tai, 2.0, 3.0]
        self.track_table_formatter.check_track_table_input_valid(table, self.future_time_s)
        assert not self.logger.info.called

    def test_track_table_input_invalid_time(self):
        """Test when future time check fails"""
        offset_s = -0.1
        time_future_unix = time() + self.future_time_s + offset_s
        time_future_tai = self.track_table_formatter.get_tai_from_unix_s(time_future_unix)
        table = [time_future_tai, 2.0, 3.0]
        self.track_table_formatter.check_track_table_input_valid(table, self.future_time_s)
        assert self.logger.info.called

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
        assert self.logger.warn.called
