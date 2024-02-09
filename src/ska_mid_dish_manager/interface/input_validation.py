"""Module for containing input validation and formatting needed for translation
between DSC and DS manager."""

from time import time
from typing import List

from astropy.time import Time


class TrackTableTimestampError(ValueError):
    """Class that is used to represent timestamp errors in the track load table"""


class TrackLoadTableFormatting:
    """Class that encapsulates related validation and mapping for TrackLoadTable command"""

    def check_track_table_input_valid(self, table: List[float], future_time_s: int) -> None:
        """Entry point for track table validation"""
        length_of_table = len(table)
        # length validaton
        if length_of_table > 0:
            # Checks that the table length is a multiple of 3
            if length_of_table % 3 != 0:
                raise ValueError(
                    f"Length of table ({len(table)}) is not a multiple of 3 "
                    "(timestamp, azimuth coordinate, elevation coordinate) as expected."
                )
            # log if samples are not in the future by future_time_s
            try:
                self._check_timestamp(table, length_of_table, future_time_s)
            except TrackTableTimestampError as timestamp_error:
                raise timestamp_error

    def get_tai_from_unix_s(self, unix_s: float) -> float:
        """Calculate atomic time in seconds from unix time in seconds"""
        astropy_time_utc = Time(unix_s, format="unix")
        return astropy_time_utc.tai

    def _check_timestamp(
        self, table: List[float], length_of_table: int, future_time_s: float
    ) -> None:
        """Check that the timestamps are in the future by at least future_time_s"""
        # use current time as reference for checking all the timestamps in the array
        # as this operation should complete fast in comparison to future_time_s
        current_time_tai_s = self.get_tai_from_unix_s(time())
        for i in range(0, length_of_table, 3):
            timestamp_tai_s = table[i]
            if timestamp_tai_s - current_time_tai_s < future_time_s:
                raise TrackTableTimestampError(
                    "Check track table parameters."
                    f"Timestamps less than {future_time_s}s into the future."
                )
