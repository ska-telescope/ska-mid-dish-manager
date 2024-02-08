"""Unit tests for input validation of of track table."""

from time import perf_counter, time
from unittest.mock import Mock

import pytest
from astropy.time import Time

from ska_mid_dish_manager.interface.input_validation import TrackLoadTableFormatting

MAX_TRACK_LOAD_TABLE_SAMPLES = 50
MAX_TAI_COMPUTATION_TIME_S = 0.15


# pylint:disable=attribute-defined-outside-init
@pytest.mark.unit
@pytest.mark.forked
class TestTrackLoadTableFormatting:
    """Tests for TrackLoadTableFormatting"""

    def setup_method(self):
        """Set up context"""
        self.logger = Mock()

    def test_track_table_input_happy(self):
        """Test happy path when length and future time is appropriate"""
        future_time_ms = 5000
        offset_ms = 100
        time_future = time() * 1e3 + future_time_ms + offset_ms
        table = [time_future, 2.0, 3.0]
        TrackLoadTableFormatting.check_track_table_input_valid(self.logger, table, future_time_ms)
        assert not self.logger.info.called

    def test_track_table_input_invalid_time(self):
        """Test when future time check fails"""
        future_time_ms = 5000
        offset_ms = -100
        time_future = time() * 1e3 + future_time_ms + offset_ms
        table = [time_future, 2.0, 3.0]
        TrackLoadTableFormatting.check_track_table_input_valid(self.logger, table, future_time_ms)
        assert self.logger.info.called

    def test_track_table_input_invalid_length(self):
        """Test when table length is invalid"""
        future_time_ms = 5000
        offset_ms = 100
        time_future = time() * 1e3 + future_time_ms + offset_ms
        table = [time_future, 2.0, 3.0, 4.0]
        with pytest.raises(ValueError):
            TrackLoadTableFormatting.check_track_table_input_valid(
                self.logger, table, future_time_ms
            )

    def test_track_table_input_empty_list(self):
        """Test when table length is empty"""
        future_time_ms = 5000
        table = []
        TrackLoadTableFormatting.check_track_table_input_valid(self.logger, table, future_time_ms)
        assert self.logger.warn.called

    def test_track_table_time_unixms_to_tai_s(self):
        """Test unix ms to tai s conversion"""
        now = time() * 1e3
        future_time_ms = 5000
        offset = 100
        unix_time_ms = now + future_time_ms + offset
        table = [unix_time_ms, 2.0, 3.0]
        astropy_time_now = Time(table[0] / 1e3, format="unix")
        TrackLoadTableFormatting.format_track_table_time_unixms_to_tai(table)
        assert table[0] == astropy_time_now

    def test_track_table_check_tai_computation_time(self):
        """Test unix ms to tai s conversion time for large arrays"""
        track_table = []
        # use starting time 30s from now
        start_time_offset_ms = (30 + time()) * 1e3
        for n in range(0, MAX_TRACK_LOAD_TABLE_SAMPLES):
            # increment time by 1 second and add dummy el and az
            track_table.extend([start_time_offset_ms + n, 0, 0])

        t1 = perf_counter()
        TrackLoadTableFormatting.format_track_table_time_unixms_to_tai(track_table)
        t2 = perf_counter()
        delta = t2 - t1
        assert (
            abs(delta) < MAX_TAI_COMPUTATION_TIME_S
        ), "NB. Speedup can be made by passing vectors to astropy libraries."
